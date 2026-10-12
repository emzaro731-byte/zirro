import base64, io, json, os, urllib.request, urllib.error
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
MAX_HISTORY = 16
SYSTEM_PROMPTS = {
 "chat": "You are ZIRRO, a capable, warm, precise all-purpose AI assistant. Be useful, honest about uncertainty, and format answers clearly.",
 "write": "You are ZIRRO Writer, an expert editor and creative writer. Produce polished, audience-aware writing.",
 "code": "You are ZIRRO Code Studio, a senior software engineer. Give secure, maintainable code, explain choices, and state assumptions.",
 "research": "You are ZIRRO Research Lab. Analyze carefully, use provided web search results when present, cite source URLs from those results, and never fabricate citations.",
 "image": "You are ZIRRO Image Studio. Analyze uploaded images and help develop visual concepts. Do not claim to generate image files.",
 "documents": "You are ZIRRO Document Intelligence. Analyze the attached document text and clearly state when content is missing."
}

def post_json(url, payload, headers=None, timeout=45):
    data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json"}
    if headers: h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())

def search_web(query):
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return None, "Web search needs the optional TAVILY_API_KEY environment variable."
    try:
        result = post_json("https://api.tavily.com/search", {
            "api_key": key, "query": query[:400], "search_depth": "basic",
            "max_results": 5, "include_answer": False
        }, timeout=25)
        lines = []
        for item in result.get("results", [])[:5]:
            lines.append(f"- {item.get('title','Source')}\n  URL: {item.get('url','')}\n  Summary: {item.get('content','')[:900]}")
        return "\n".join(lines), None
    except Exception:
        app.logger.exception("Web search failed")
        return None, "Web search is temporarily unavailable."

@app.get("/")
def home():
    return send_from_directory(".", "index.html")

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "app": "ZIRRO AI",
        "provider_configured": bool(os.getenv("OPENROUTER_API_KEY")),
        "web_search_configured": bool(os.getenv("TAVILY_API_KEY")),\n        "huggingface_embeddings_configured": bool(os.getenv("HF_TOKEN")),\n        "embedding_model": os.getenv("HF_EMBEDDING_MODEL", "Emma11122/embeddinggemma-2-bucket"),
        "pdf_support": True})

@app.post("/api/embeddings")
def embeddings():
    """Create text embeddings for semantic search / document retrieval.
    This is separate from chat and does not generate user-facing prose or images.
    """
    token = os.getenv("HF_TOKEN")
    if not token:
        return jsonify({"error": "Embeddings are not configured. Add HF_TOKEN in Render Environment."}), 503
    body = request.get_json(silent=True) or {}
    inputs = body.get("inputs", body.get("text", ""))
    if isinstance(inputs, str):
        inputs = [inputs]
    if not isinstance(inputs, list) or not inputs or len(inputs) > 32:
        return jsonify({"error": "Send 'text' as a string or 'inputs' as a list of 1–32 strings."}), 400
    if any(not isinstance(value, str) or not value.strip() for value in inputs):
        return jsonify({"error": "Every input must be a non-empty string."}), 400
    if any(len(value) > 8000 for value in inputs):
        return jsonify({"error": "Each input must be at most 8,000 characters."}), 413
    model = os.getenv("HF_EMBEDDING_MODEL", "Emma11122/embeddinggemma-2-bucket")
    try:
        url = "https://router.huggingface.co/hf-inference/models/" + model
        result = post_json(url, {"inputs": inputs, "options": {"wait_for_model": True}}, {
            "Authorization": "Bearer " + token
        }, timeout=100)
        # Feature-extraction APIs normally return a list of vectors. Keep the
        # provider response intact because models may return nested vectors.
        if isinstance(result, dict) and result.get("error"):
            return jsonify({"error": str(result["error"])[:350], "model": model}), 502
        return jsonify({"ok": True, "model": model, "embeddings": result})
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode()).get("error", "Hugging Face inference request failed")
        except Exception:
            detail = "Hugging Face inference request failed"
        return jsonify({"error": str(detail)[:350], "model": model,
                        "hint": "Confirm the model supports feature extraction and is available through Hugging Face Inference Providers."}), 502
    except Exception:
        app.logger.exception("Hugging Face embedding request failed")
        return jsonify({"error": "Could not reach Hugging Face inference. Try again shortly.", "model": model}), 502

@app.post("/api/chat")
def chat():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return jsonify({"error": "Free AI provider is not configured. Add OPENROUTER_API_KEY in your hosting environment variables."}), 503
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()
    mode = body.get("mode", "chat")
    attachments = body.get("attachments") or []
    if not message and not attachments:
        return jsonify({"error": "Write a message or attach a supported file."}), 400
    if len(message) > 20000:
        return jsonify({"error": "Message is too long (maximum 20,000 characters)."}), 413
    system = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["chat"])
    if body.get("web_search") and message:
        results, error = search_web(message)
        if results:
            system += "\n\nLive web search results retrieved for this request. Use only these sources for current factual claims, and cite URLs exactly as provided. If results do not answer the question, say so.\n" + results
        elif error:
            system += "\n\n" + error
    messages = [{"role":"system","content":system}]
    history = body.get("history", [])
    for item in history[-MAX_HISTORY:]:
        role, content = item.get("role"), item.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role":role, "content":content[:12000]})
    parts = []
    if message: parts.append({"type":"text","text":message})
    for item in attachments[:4]:
        kind = item.get("type")
        if kind == "image":
            data = item.get("data", "")
            if isinstance(data, str) and data.startswith("data:image/") and len(data) < 8*1024*1024:
                parts.append({"type":"image_url","image_url":{"url":data}})
        elif kind == "text" and isinstance(item.get("text"), str):
            parts.append({"type":"text","text":"Attached file "+str(item.get("name","file"))+":\n"+item["text"][:16000]})
        elif kind == "pdf" and isinstance(item.get("data"), str):
            try:
                from pypdf import PdfReader
                raw = item["data"].split(",",1)[-1]
                pdf = PdfReader(io.BytesIO(base64.b64decode(raw)))
                extracted = "\n".join((p.extract_text() or "") for p in pdf.pages[:40])
                parts.append({"type":"text","text":"Extracted PDF text from "+str(item.get("name","document.pdf"))+":\n"+extracted[:24000]})
            except Exception:
                parts.append({"type":"text","text":"Could not extract readable text from PDF "+str(item.get("name","document.pdf"))+". It may be scanned or protected."})
    content = parts if any(p["type"] == "image_url" for p in parts) else "\n\n".join(p["text"] for p in parts if p["type"] == "text")
    messages.append({"role":"user","content":content or message})
    payload = {"model":os.getenv("OPENROUTER_MODEL","openrouter/free"),"messages":messages,"temperature":0.7}
    try:
        result = post_json("https://openrouter.ai/api/v1/chat/completions", payload, {
            "Authorization":"Bearer "+key,
            "HTTP-Referer":os.getenv("APP_URL","https://github.com/emzaro731-byte/zirro"),
            "X-Title":"ZIRRO AI"
        }, timeout=100)
        answer = result.get("choices",[{}])[0].get("message",{}).get("content","")
        if isinstance(answer,list):
            answer = "\n".join(p.get("text","") for p in answer if isinstance(p,dict))
        if not answer: return jsonify({"error":"The AI provider returned an empty response. Try again."}), 502
        return jsonify({"reply":answer,"model":result.get("model",payload["model"]),
                        "web_search_used":bool(body.get("web_search") and os.getenv("TAVILY_API_KEY"))})
    except urllib.error.HTTPError as exc:
        try: detail=json.loads(exc.read().decode()).get("error",{}).get("message","Provider request failed")
        except Exception: detail="Provider request failed"
        return jsonify({"error":"AI provider error: "+str(detail)[:350]}), 502
    except Exception:
        app.logger.exception("AI request failed")
        return jsonify({"error":"Could not reach the AI provider. Please try again shortly."}), 502

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error":"Upload too large. Keep total request under 12 MB."}), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")))
