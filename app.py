import json, os, urllib.request, urllib.error
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder=".", static_url_path="")
MAX_HISTORY = 16
SYSTEM_PROMPTS = {
 "chat": "You are ZIRRO, a capable, warm, precise all-purpose AI assistant. Be useful, honest about uncertainty, and format answers clearly.",
 "write": "You are ZIRRO Writer, an expert editor and creative writer. Produce polished, audience-aware writing and ask only essential clarifying questions.",
 "code": "You are ZIRRO Code Studio, a senior software engineer. Give correct, secure, maintainable code, explain important choices, and state assumptions.",
 "research": "You are ZIRRO Research Lab. Analyze carefully, distinguish established facts from uncertainty, and never fabricate citations or claim to have browsed when you have not.",
 "image": "You are ZIRRO Image Studio. Help develop visual concepts and analyze uploaded images. Be clear that this endpoint analyzes images and does not itself generate image files.",
 "documents": "You are ZIRRO Document Intelligence. Summarize and analyze only the document text provided; clearly state when content is missing."
}

@app.get("/")
def home():
    return send_from_directory(".", "index.html")

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "app": "ZIRRO AI", "provider_configured": bool(os.getenv("OPENROUTER_API_KEY"))})

@app.post("/api/chat")
def chat():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return jsonify({"error": "Free AI provider is not configured. Add OPENROUTER_API_KEY in your hosting environment variables."}), 503
    body = request.get_json(silent=True) or {}
    message = str(body.get("message", "")).strip()
    mode = body.get("mode", "chat")
    if not message and not body.get("attachments"):
        return jsonify({"error": "Write a message or attach a supported image/text file."}), 400
    if len(message) > 20000:
        return jsonify({"error": "Message is too long (maximum 20,000 characters)."}), 413
    history = body.get("history", [])
    messages = [{"role":"system","content":SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["chat"])}]
    for item in history[-MAX_HISTORY:]:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content[:12000]})
    user_content = []
    if message:
        user_content.append({"type":"text","text":message})
    for item in (body.get("attachments") or [])[:4]:
        if item.get("type") == "image":
            data = item.get("data", "")
            if isinstance(data, str) and data.startswith("data:image/") and len(data) < 8*1024*1024:
                user_content.append({"type":"image_url","image_url":{"url":data}})
        elif item.get("type") == "text" and isinstance(item.get("text"), str):
            user_content.append({"type":"text","text":"Attached file "+str(item.get("name","file"))+":\n"+item["text"][:12000]})
    messages.append({"role":"user","content":user_content if len(user_content)>1 or (user_content and user_content[0]["type"]=="image_url") else (user_content[0]["text"] if user_content else message)})
    payload = {"model": os.getenv("OPENROUTER_MODEL", "openrouter/free"), "messages": messages, "temperature": 0.7}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Authorization":"Bearer "+key,"Content-Type":"application/json","HTTP-Referer":os.getenv("APP_URL","https://github.com/emzaro731-byte/zirro"),"X-Title":"ZIRRO AI"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            result = json.loads(response.read().decode())
        answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(answer, list):
            answer = "\n".join(part.get("text","") for part in answer if isinstance(part,dict))
        if not answer:
            return jsonify({"error":"The AI provider returned an empty response. Try again."}), 502
        return jsonify({"reply": answer, "model": result.get("model", payload["model"])})
    except urllib.error.HTTPError as exc:
        try:
            details = json.loads(exc.read().decode()).get("error", {}).get("message", "Provider request failed")
        except Exception:
            details = "Provider request failed"
        return jsonify({"error":"AI provider error: "+str(details)[:350]}), 502
    except Exception:
        app.logger.exception("AI request failed")
        return jsonify({"error":"Could not reach the AI provider. Please try again shortly."}), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
