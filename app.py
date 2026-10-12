import base64, io, json, os, urllib.request, urllib.error
from flask import Flask, request, jsonify, send_from_directory, Response

app = Flask(__name__, static_folder=".", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
MAX_HISTORY = 16
SYSTEM_PROMPTS = {
 "chat": "You are ZIRRO, a capable, warm, precise all-purpose AI assistant. Be useful, honest about uncertainty, and format answers clearly.",
 "write": "You are ZIRRO Writer, an expert editor and creative writer. Produce polished, audience-aware writing.",
 "code": "You are ZIRRO Code Studio, a senior software engineer. Give secure, maintainable code, explain choices, and state assumptions.",
 "research": "You are ZIRRO Research Lab. Analyze carefully, use provided web search results when present, cite source URLs from those results, and never fabricate citations.",
 "image": "You are ZIRRO Image Studio. Analyze uploaded images and help develop visual concepts. Do not claim to generate image files.",
 "documents": "You are ZIRRO Document Intelligence. Analyze the attached document text and clearly state when content is missing.",
 "security": "You are ZIRRO Security Lab, a defensive cybersecurity assistant. Help users secure their own devices, accounts, applications, and systems they are explicitly authorized to assess. Prioritize safe configuration, threat modeling, secure coding, vulnerability explanation, log interpretation, patching, and remediation. For testing, keep guidance scoped to authorized lab environments and non-destructive validation. Do not help steal credentials, deploy malware, evade detection, persist on systems, exploit real targets without authorization, or disrupt services. When a request could target a third party, clarify authorization and redirect to defensive alternatives. Never claim ZIRRO has scanned or tested a target unless a tool actually did so."
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
        "groq_fallback_configured": bool(os.getenv("GROQ_API_KEY")),
        "chat_failover": True,
        "image_generation_configured": bool(os.getenv("OPENROUTER_API_KEY")),
        "video_generation_configured": bool(os.getenv("OPENROUTER_API_KEY")),
        "video_model": os.getenv("OPENROUTER_VIDEO_MODEL", "google/veo-3.1"),
        "music_generation_configured": bool(os.getenv("REPLICATE_API_TOKEN")),
        "music_provider": "Replicate MusicGen",
        "image_model": os.getenv("OPENROUTER_IMAGE_MODEL", "google/gemini-3.1-flash-image"),
        "web_search_configured": bool(os.getenv("TAVILY_API_KEY")),
        "embeddings_configured": bool(os.getenv("OPENROUTER_API_KEY")),
        "embedding_model": os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small"),
        "pdf_support": True, "image_upload": True, "video_upload": "sampled_frames", "text_file_upload": True})


PLUGIN_CATALOG = [
    {"id": "openrouter", "name": "OpenRouter AI", "type": "connector", "feature": "chat", "env": "OPENROUTER_API_KEY"},
    {"id": "openai", "name": "ChatGPT / OpenAI", "type": "connector", "feature": "chat", "env": "OPENAI_API_KEY"},
    {"id": "grok", "name": "Grok by xAI", "type": "connector", "feature": "chat", "env": "XAI_API_KEY"},
    {"id": "gemini", "name": "Google Gemini", "type": "connector", "feature": "chat", "env": "GEMINI_API_KEY"},
    {"id": "perplexity", "name": "Perplexity AI", "type": "connector", "feature": "chat", "env": "PERPLEXITY_API_KEY"},
    {"id": "tavily", "name": "Tavily Web Search", "type": "connector", "feature": "search", "env": "TAVILY_API_KEY"},
    {"id": "imagegen", "name": "Image Generation", "type": "plugin", "feature": "image", "env": "OPENROUTER_API_KEY"},
    {"id": "documents", "name": "Document Intelligence", "type": "plugin", "feature": "documents", "env": None},
    {"id": "voice", "name": "Voice Tools", "type": "plugin", "feature": "browser", "env": None},
    {"id": "embeddings", "name": "Semantic Search", "type": "connector", "feature": "embeddings", "env": "OPENROUTER_API_KEY"},
    {"id": "custom-api", "name": "Custom API Endpoint", "type": "connector", "feature": "planned", "env": None},
    {"id": "prompt-library", "name": "Prompt Library", "type": "plugin", "feature": "local", "env": None},
]

@app.get("/api/plugins")
def plugins():
    """Return safe plugin metadata and configuration state; never expose secret values."""
    health = {
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "grok": bool(os.getenv("XAI_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "perplexity": bool(os.getenv("PERPLEXITY_API_KEY")),
        "tavily": bool(os.getenv("TAVILY_API_KEY")),
        "imagegen": bool(os.getenv("OPENROUTER_API_KEY")),
        "documents": True,
        "voice": True,
        "embeddings": bool(os.getenv("OPENROUTER_API_KEY")),
        "custom-api": False,
        "prompt-library": True,
    }
    items = []
    for plugin in PLUGIN_CATALOG:
        item = dict(plugin)
        item.pop("env", None)
        item["configured"] = health.get(plugin["id"], False)
        item["status"] = (
            "configured" if item["configured"] and plugin["feature"] not in ("planned",)
            else "needs_setup" if plugin["env"] and not item["configured"]
            else "preview" if plugin["feature"] == "planned"
            else "available"
        )
        items.append(item)
    return jsonify({"ok": True, "plugins": items})


@app.post("/api/plugins/<plugin_id>/test")
def test_plugin(plugin_id):
    """Check connector readiness without exposing secrets or generating billable content."""
    known = {item["id"]: item for item in PLUGIN_CATALOG}
    plugin = known.get(plugin_id)
    if not plugin:
        return jsonify({"ok": False, "error": "Unknown plugin."}), 404
    provider_checks = {
        "openai": ("OPENAI_API_KEY", "https://api.openai.com/v1/models", "ChatGPT / OpenAI"),
        "grok": ("XAI_API_KEY", "https://api.x.ai/v1/models", "Grok / xAI"),
        "gemini": ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/models", "Google Gemini"),
        "perplexity": ("PERPLEXITY_API_KEY", "https://api.perplexity.ai/chat/completions", "Perplexity AI"),
    }
    if plugin_id in provider_checks:
        env_name, url, provider_name = provider_checks[plugin_id]
        token = os.getenv(env_name)
        if not token:
            return jsonify({"ok": False, "status": "needs_setup", "message": "Add " + env_name + " in your Render Environment settings, then redeploy."}), 503
        try:
            if plugin_id == "perplexity":
                req = urllib.request.Request(url, data=json.dumps({"model":"sonar","messages":[{"role":"user","content":"Reply with OK"}],"max_tokens":2}).encode(), headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"}, method="POST")
            else:
                req = urllib.request.Request(url, headers={"Authorization":"Bearer "+token})
            with urllib.request.urlopen(req, timeout=20) as response:
                if 200 <= response.status < 300:
                    return jsonify({"ok": True, "status": "connected", "message": provider_name + " API responded successfully."})
        except urllib.error.HTTPError as exc:
            return jsonify({"ok": False, "status": "error", "message": provider_name + " returned HTTP " + str(exc.code) + ". Check the API key, provider access, and account limits."}), 502
        except Exception:
            return jsonify({"ok": False, "status": "error", "message": "Could not reach " + provider_name + ". Try again shortly."}), 502
    if plugin_id == "openrouter":
        token = os.getenv("OPENROUTER_API_KEY")
        if not token:
            return jsonify({"ok": False, "status": "needs_setup", "message": "Set OPENROUTER_API_KEY in your Render environment."}), 503
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"Authorization": "Bearer " + token})
            with urllib.request.urlopen(req, timeout=20) as response:
                if response.status == 200:
                    return jsonify({"ok": True, "status": "connected", "message": "OpenRouter responded successfully. No generation request was sent."})
        except urllib.error.HTTPError as exc:
            return jsonify({"ok": False, "status": "error", "message": "OpenRouter returned HTTP " + str(exc.code) + ". Check the API key and provider status."}), 502
        except Exception:
            return jsonify({"ok": False, "status": "error", "message": "Could not reach OpenRouter. Try again shortly."}), 502
    if plugin_id == "tavily":
        if not os.getenv("TAVILY_API_KEY"):
            return jsonify({"ok": False, "status": "needs_setup", "message": "Set TAVILY_API_KEY in your Render environment."}), 503
        _, error = search_web("ZIRRO AI connector test")
        if error:
            return jsonify({"ok": False, "status": "error", "message": error}), 502
        return jsonify({"ok": True, "status": "connected", "message": "Tavily search responded successfully."})
    if plugin_id in ("imagegen", "embeddings"):
        if not os.getenv("OPENROUTER_API_KEY"):
            return jsonify({"ok": False, "status": "needs_setup", "message": "Set OPENROUTER_API_KEY in your Render environment."}), 503
        if plugin_id == "imagegen":
            return jsonify({"ok": True, "status": "configured", "message": "Provider key is configured. Image generation still depends on model support and available credits; no image was generated during this check."})
        return jsonify({"ok": True, "status": "configured", "message": "Provider key is configured. No embedding request was sent during this check."})
    if plugin_id == "custom-api":
        return jsonify({"ok": False, "status": "preview", "message": "This adapter is not implemented yet. No endpoint or credentials have been saved."}), 501
    return jsonify({"ok": True, "status": "available", "message": "This feature uses built-in or browser-native functionality; no external API key is required."})

@app.post("/api/search")
def api_search():
    """Run an actual Tavily search using a server-side secret."""
    body = request.get_json(silent=True) or {}
    query = str(body.get("query", "")).strip()
    if not query:
        return jsonify({"error": "Enter a search query."}), 400
    if len(query) > 400:
        return jsonify({"error": "Search query must be 400 characters or fewer."}), 413
    results, error = search_web(query)
    if error:
        status = 503 if not os.getenv("TAVILY_API_KEY") else 502
        return jsonify({"ok": False, "error": error}), status
    items = []
    for line in (results or "").splitlines():
        if line.startswith("- "):
            items.append({"title": line[2:].strip()})
        elif line.strip().startswith("URL: ") and items:
            items[-1]["url"] = line.strip()[5:]
        elif line.strip().startswith("Summary: ") and items:
            items[-1]["summary"] = line.strip()[9:]
    return jsonify({"ok": True, "query": query, "results": items})

@app.post("/api/embeddings")
def embeddings():
    """Create text embeddings through OpenRouter for semantic search / retrieval."""
    token = os.getenv("OPENROUTER_API_KEY")
    if not token:
        return jsonify({"error": "Add OPENROUTER_API_KEY in Render Environment."}), 503
    body = request.get_json(silent=True) or {}
    inputs = body.get("input", body.get("inputs", body.get("text", "")))
    if isinstance(inputs, str):
        inputs = [inputs]
    if not isinstance(inputs, list) or not inputs or len(inputs) > 32:
        return jsonify({"error": "Send 'input' as a string or a list of 1–32 strings."}), 400
    if any(not isinstance(value, str) or not value.strip() for value in inputs):
        return jsonify({"error": "Every input must be a non-empty string."}), 400
    if any(len(value) > 8000 for value in inputs):
        return jsonify({"error": "Each input must be at most 8,000 characters."}), 413
    model = os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small")
    try:
        result = post_json("https://openrouter.ai/api/v1/embeddings", {
            "model": model, "input": inputs, "encoding_format": "float"
        }, {
            "Authorization": "Bearer " + token,
            "HTTP-Referer": os.getenv("APP_URL", "https://github.com/emzaro731-byte/zirro"),
            "X-Title": "ZIRRO AI"
        }, timeout=100)
        if isinstance(result, dict) and result.get("error"):
            detail = result["error"]
            if isinstance(detail, dict):
                detail = detail.get("message", "OpenRouter embeddings request failed")
            return jsonify({"error": str(detail)[:350], "model": model}), 502
        return jsonify({"ok": True, "model": result.get("model", model),
                        "data": result.get("data", []), "usage": result.get("usage", {})})
    except urllib.error.HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode()).get("error", {})
            detail = error_body.get("message", "OpenRouter embeddings request failed") if isinstance(error_body, dict) else str(error_body)
        except Exception:
            detail = "OpenRouter embeddings request failed"
        return jsonify({"error": str(detail)[:350], "model": model,
                        "hint": "The selected OpenRouter embedding model may require credits. Check the model's pricing and availability."}), 502
    except Exception:
        app.logger.exception("OpenRouter embeddings request failed")
        return jsonify({"error": "Could not reach OpenRouter embeddings. Try again shortly.", "model": model}), 502

@app.post("/api/generate-image")
def generate_image():
    """Generate an image using an OpenRouter model that supports image output."""
    body = request.get_json(silent=True) or {}
    # User-supplied keys are used for this request only and are never persisted.
    token = str(body.get("api_key", "")).strip() or os.getenv("OPENROUTER_API_KEY")
    if not token:
        return jsonify({"error": "Add your OpenRouter API key with “My API Key”, or configure OPENROUTER_API_KEY in Render."}), 503
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"error": "Describe the image you want to create."}), 400
    if len(prompt) > 4000:
        return jsonify({"error": "Prompt is too long (maximum 4,000 characters)."}), 413
    model = os.getenv("OPENROUTER_IMAGE_MODEL", "google/gemini-3.1-flash-image")
    try:
        result = post_json("https://openrouter.ai/api/v1/chat/completions", {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"]
        }, {
            "Authorization": "Bearer " + token,
            "HTTP-Referer": os.getenv("APP_URL", "https://github.com/emzaro731-byte/zirro"),
            "X-Title": "ZIRRO AI Image Studio"
        }, timeout=120)
        if isinstance(result, dict) and result.get("error"):
            detail = result["error"]
            if isinstance(detail, dict):
                detail = detail.get("message", "Image generation request failed")
            return jsonify({"error": str(detail)[:350], "model": model}), 502
        message = result.get("choices", [{}])[0].get("message", {})
        images = message.get("images") or []
        image_url = None
        if images and isinstance(images[0], dict):
            image_url = (images[0].get("image_url") or {}).get("url")
        if not image_url:
            for part in message.get("content", []) if isinstance(message.get("content"), list) else []:
                if isinstance(part, dict) and part.get("type") in ("image_url", "image"):
                    image_url = (part.get("image_url") or {}).get("url") or part.get("url")
                    if image_url:
                        break
        if not isinstance(image_url, str) or not image_url.startswith("data:image/"):
            return jsonify({"error": "The selected model did not return an image. Check that OPENROUTER_IMAGE_MODEL supports image generation, then try again.", "model": result.get("model", model)}), 502
        return jsonify({"ok": True, "image": image_url, "model": result.get("model", model)})
    except urllib.error.HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode()).get("error", {})
            detail = error_body.get("message", "Image generation request failed") if isinstance(error_body, dict) else str(error_body)
        except Exception:
            detail = "Image generation request failed"
        detail_text = str(detail)[:350]
        lower_detail = detail_text.lower()
        if any(word in lower_detail for word in ("insufficient", "balance", "credit", "requires at least $1")):
            return jsonify({"error": "Image provider error: " + detail_text,
                            "hint": "The provider requires available account credits for image output. Add credits in your OpenRouter account or choose a model/provider with pricing you can afford. Setting an API key alone does not provide free image generation.",
                            "model": model}), 402
        return jsonify({"error": "Image provider error: " + detail_text,
                        "hint": "Check that OPENROUTER_IMAGE_MODEL supports image output and that the provider is available."}), 502
    except Exception:
        app.logger.exception("Image generation failed")
        return jsonify({"error": "Could not reach the image provider. Please try again shortly."}), 502



def _provider_error(exc, fallback):
    try:
        data = json.loads(exc.read().decode())
        error = data.get("error", data)
        if isinstance(error, dict):
            return str(error.get("message") or error.get("detail") or fallback)[:500]
        return str(error)[:500]
    except Exception:
        return fallback


@app.get("/api/video/models")
def video_models():
    token = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not token:
        return jsonify({"ok": False, "error": "Configure OPENROUTER_API_KEY in Render to list available video models."}), 503
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/videos/models",
            headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.loads(response.read().decode())
        models = []
        for item in data.get("data", [])[:100]:
            models.append({"id": item.get("id"), "name": item.get("name") or item.get("id"),
                "supported_durations": item.get("supported_durations", []),
                "supported_resolutions": item.get("supported_resolutions", []),
                "supported_aspect_ratios": item.get("supported_aspect_ratios", []),
                "pricing_skus": item.get("pricing_skus", {})})
        return jsonify({"ok": True, "models": models})
    except urllib.error.HTTPError as exc:
        return jsonify({"ok": False, "error": "OpenRouter model discovery failed: " + _provider_error(exc, "Provider request failed")}), 502
    except Exception:
        app.logger.exception("Video model discovery failed")
        return jsonify({"ok": False, "error": "Could not load video models right now."}), 502


@app.post("/api/generate-video")
def generate_video():
    body = request.get_json(silent=True) or {}
    token = str(body.get("api_key", "")).strip() or os.getenv("OPENROUTER_API_KEY", "").strip()
    if not token:
        return jsonify({"ok": False, "error": "Add OPENROUTER_API_KEY in Render Environment. Video generation is not included automatically with a chat key's free quota."}), 503
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"ok": False, "error": "Describe the video you want to create."}), 400
    if len(prompt) > 4000:
        return jsonify({"ok": False, "error": "Prompt must be 4,000 characters or fewer."}), 413
    model = str(body.get("model") or os.getenv("OPENROUTER_VIDEO_MODEL", "google/veo-3.1")).strip()
    allowed_durations = (4, 5, 6, 8, 10, 12)
    try:
        duration = int(body.get("duration", 5))
    except (TypeError, ValueError):
        duration = 5
    if duration not in allowed_durations:
        return jsonify({"ok": False, "error": "Duration must be one of: 4, 5, 6, 8, 10, or 12 seconds. The selected model may support fewer options."}), 400
    resolution = str(body.get("resolution", "720p"))
    aspect_ratio = str(body.get("aspect_ratio", "16:9"))
    payload = {"model": model, "prompt": prompt, "duration": duration,
               "resolution": resolution, "aspect_ratio": aspect_ratio,
               "generate_audio": bool(body.get("generate_audio", True))}
    try:
        result = post_json("https://openrouter.ai/api/v1/videos", payload, {
            "Authorization": "Bearer " + token, "HTTP-Referer": os.getenv("APP_URL", "https://github.com/emzaro731-byte/zirro"),
            "X-Title": "ZIRRO AI Video Studio"}, timeout=45)
        job_id = result.get("id") or result.get("job_id")
        if not job_id:
            return jsonify({"ok": False, "error": "OpenRouter did not return a video job ID.", "details": result}), 502
        return jsonify({"ok": True, "job_id": str(job_id), "status": result.get("status", "pending"),
                        "model": model, "message": "Video job submitted. It may take several minutes and may incur provider charges."}), 202
    except urllib.error.HTTPError as exc:
        detail = _provider_error(exc, "Video generation request failed")
        status = 402 if exc.code == 402 or any(w in detail.lower() for w in ("balance", "credit", "insufficient")) else 502
        return jsonify({"ok": False, "error": detail, "hint": "Check the selected model's current pricing, your OpenRouter balance, and model-supported duration/resolution."}), status
    except Exception:
        app.logger.exception("Video generation request failed")
        return jsonify({"ok": False, "error": "Could not reach OpenRouter video generation. Try again shortly."}), 502


@app.get("/api/video/status/<job_id>")
def video_status(job_id):
    if not job_id or len(job_id) > 180 or not all(c.isalnum() or c in "-_." for c in job_id):
        return jsonify({"ok": False, "error": "Invalid video job ID."}), 400
    token = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not token:
        return jsonify({"ok": False, "error": "OPENROUTER_API_KEY is not configured."}), 503
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/videos/" + job_id,
            headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=25) as response:
            result = json.loads(response.read().decode())
        urls = result.get("unsigned_urls") or []
        return jsonify({"ok": True, "job_id": job_id, "status": result.get("status", "unknown"),
                        "error": result.get("error"), "video_url": urls[0] if urls else None,
                        "usage": result.get("usage"), "model": result.get("model")})
    except urllib.error.HTTPError as exc:
        return jsonify({"ok": False, "error": _provider_error(exc, "Could not read video job status.")}), 502
    except Exception:
        app.logger.exception("Video status check failed")
        return jsonify({"ok": False, "error": "Could not check video status. Try again shortly."}), 502


@app.get("/api/video/content/<job_id>")
def video_content(job_id):
    if not job_id or len(job_id) > 180 or not all(c.isalnum() or c in "-_." for c in job_id):
        return jsonify({"ok": False, "error": "Invalid video job ID."}), 400
    token = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not token:
        return jsonify({"ok": False, "error": "OPENROUTER_API_KEY is not configured."}), 503
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/videos/" + job_id + "/content?index=0",
            headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=90) as upstream:
            content = upstream.read()
            content_type = upstream.headers.get("Content-Type", "video/mp4")
        return Response(content, mimetype=content_type, headers={"Content-Disposition": 'attachment; filename="zirro-video.mp4"', "Cache-Control": "no-store"})
    except urllib.error.HTTPError as exc:
        return jsonify({"ok": False, "error": _provider_error(exc, "Video content is not ready yet.")}), 502
    except Exception:
        app.logger.exception("Video download failed")
        return jsonify({"ok": False, "error": "Could not download the generated video."}), 502


@app.post("/api/generate-music")
def generate_music():
    body = request.get_json(silent=True) or {}
    token = os.getenv("REPLICATE_API_TOKEN", "").strip()
    if not token:
        return jsonify({"ok": False, "error": "Music generation needs a Replicate API token. Add REPLICATE_API_TOKEN in Render Environment; OpenRouter does not currently provide general text-to-music generation through its standard audio endpoint.", "setup_url": "https://replicate.com/account/api-tokens"}), 503
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"ok": False, "error": "Describe the music you want to create."}), 400
    if len(prompt) > 2000:
        return jsonify({"ok": False, "error": "Music prompt must be 2,000 characters or fewer."}), 413
    try:
        duration = int(body.get("duration", 8))
    except (TypeError, ValueError):
        duration = 8
    duration = max(5, min(duration, 30))
    payload = {"input": {"prompt": prompt[:2000], "model_version": "stereo-large",
                         "output_format": "mp3", "duration": duration}}
    try:
        result = post_json("https://api.replicate.com/v1/models/meta/musicgen/predictions", payload,
            {"Authorization": "Bearer " + token, "Prefer": "wait=1"}, timeout=45)
        return jsonify({"ok": True, "prediction_id": result.get("id"), "status": result.get("status", "starting"),
                        "music_url": result.get("output") if isinstance(result.get("output"), str) else (result.get("output") or [None])[0],
                        "message": "Music generation submitted. Replicate usage is billed by its current model pricing."}), 202
    except urllib.error.HTTPError as exc:
        return jsonify({"ok": False, "error": _provider_error(exc, "Music generation request failed."),
                        "hint": "Check your Replicate token, account limits, and current MusicGen model availability."}), 502
    except Exception:
        app.logger.exception("Music generation request failed")
        return jsonify({"ok": False, "error": "Could not reach the music provider right now."}), 502


@app.get("/api/music/status/<prediction_id>")
def music_status(prediction_id):
    if not prediction_id or len(prediction_id) > 180 or not all(c.isalnum() or c in "-_." for c in prediction_id):
        return jsonify({"ok": False, "error": "Invalid music prediction ID."}), 400
    token = os.getenv("REPLICATE_API_TOKEN", "").strip()
    if not token:
        return jsonify({"ok": False, "error": "REPLICATE_API_TOKEN is not configured."}), 503
    try:
        req = urllib.request.Request("https://api.replicate.com/v1/predictions/" + prediction_id,
            headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=25) as response:
            result = json.loads(response.read().decode())
        output = result.get("output")
        if isinstance(output, list):
            output = output[0] if output else None
        return jsonify({"ok": True, "prediction_id": prediction_id, "status": result.get("status", "unknown"),
                        "music_url": output if isinstance(output, str) else None, "error": result.get("error")})
    except urllib.error.HTTPError as exc:
        return jsonify({"ok": False, "error": _provider_error(exc, "Could not read music job status.")}), 502
    except Exception:
        app.logger.exception("Music status check failed")
        return jsonify({"ok": False, "error": "Could not check music status right now."}), 502


@app.post("/api/chat")
def chat():
    body = request.get_json(silent=True) or {}
    provider = str(body.get("provider", "openrouter")).lower()
    providers = {
        "openrouter": {"env":"OPENROUTER_API_KEY","url":"https://openrouter.ai/api/v1/chat/completions","model":os.getenv("OPENROUTER_MODEL","openrouter/free"),"name":"ZIRRO AI"}
    }
    config = providers.get(provider)
    if not config:
        return jsonify({"error":"This provider has been removed from ZIRRO AI. Please use the configured ZIRRO AI engine."}), 400
    # Per-user API keys are accepted for this request only; they are not stored.
    supplied_key = body.get("api_key", "")
    if supplied_key is not None and not isinstance(supplied_key, str):
        return jsonify({"error":"API key must be a string."}), 400
    key = (supplied_key or "").strip() or os.getenv(config["env"], "")
    if len(key) > 500:
        return jsonify({"error":"API key is too long."}), 400
    # Missing primary key is handled by the Groq fallback below.
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
            system += "\\n\\nLive web search results retrieved for this request. Use only these sources for current factual claims, and cite URLs exactly as provided. If results do not answer the question, say so.\\n" + results
        elif error:
            system += "\\n\\n" + error
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
                parts.append({"type":"text","text":"Attached image: " + str(item.get("name","image"))})
                parts.append({"type":"image_url","image_url":{"url":data}})
        elif kind == "video":
            frames = item.get("frames") or []
            parts.append({"type":"text","text":"Attached video: " + str(item.get("name","video")) + ". The following are sampled frames from the video in chronological order; describe visible events and note that these are sampled frames, not the full video."})
            for frame in frames[:4]:
                data = frame.get("data", "") if isinstance(frame, dict) else ""
                if isinstance(data, str) and data.startswith("data:image/") and len(data) < 2*1024*1024:
                    stamp = frame.get("time", "?")
                    parts.append({"type":"text","text":"Video frame at approximately " + str(stamp) + " seconds:"})
                    parts.append({"type":"image_url","image_url":{"url":data}})
        elif kind == "text" and isinstance(item.get("text"), str):
            parts.append({"type":"text","text":"Attached file "+str(item.get("name","file"))+":\\n"+item["text"][:16000]})
        elif kind == "pdf" and isinstance(item.get("data"), str):
            try:
                from pypdf import PdfReader
                raw = item["data"].split(",",1)[-1]
                pdf = PdfReader(io.BytesIO(base64.b64decode(raw)))
                extracted = "\\n".join((p.extract_text() or "") for p in pdf.pages[:40])
                parts.append({"type":"text","text":"Extracted PDF text from "+str(item.get("name","document.pdf"))+":\\n"+extracted[:24000]})
            except Exception:
                parts.append({"type":"text","text":"Could not extract readable text from PDF "+str(item.get("name","document.pdf"))+". It may be scanned or protected."})
    content = parts if any(p["type"] == "image_url" for p in parts) else "\\n\\n".join(p["text"] for p in parts if p["type"] == "text")
    messages.append({"role":"user","content":content or message})

    payload = {"model":config["model"],"messages":messages,"temperature":0.7}
    def groq_fallback(reason):
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if not groq_key:
            return jsonify({"error":"OpenRouter is unavailable and Groq fallback is not configured. Add GROQ_API_KEY in Render Environment.","provider":"openrouter","fallback_available":False}), 502
        groq_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        text_parts.append("[Image/video frame attached; the default Groq fallback model cannot inspect it.]")
                content = "\n".join(text_parts)
            groq_messages.append({"role":msg.get("role","user"),"content":content})
        groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        try:
            result = post_json("https://api.groq.com/openai/v1/chat/completions",
                {"model":groq_model,"messages":groq_messages,"temperature":0.7},
                {"Authorization":"Bearer "+groq_key}, timeout=100)
            answer = result.get("choices",[{}])[0].get("message",{}).get("content","")
            if isinstance(answer, list):
                answer = "\n".join(p.get("text","") for p in answer if isinstance(p,dict))
            if not answer:
                return jsonify({"error":"OpenRouter failed and Groq returned an empty response.","provider":"groq"}), 502
            return jsonify({"reply":answer,"model":result.get("model",groq_model),"provider":"groq",
                            "fallback_used":True,"fallback_reason":str(reason)[:180],
                            "web_search_used":bool(body.get("web_search") and os.getenv("TAVILY_API_KEY"))})
        except urllib.error.HTTPError as exc:
            try:
                data = json.loads(exc.read().decode())
                error = data.get("error", {})
                detail = error.get("message", "Groq request failed") if isinstance(error,dict) else str(error)
            except Exception:
                detail = "Groq request failed"
            return jsonify({"error":"OpenRouter failed and Groq fallback also failed: "+str(detail)[:250],"provider":"groq","fallback_used":True}), 502
        except Exception:
            app.logger.exception("Groq fallback request failed")
            return jsonify({"error":"OpenRouter and Groq are both temporarily unreachable.","provider":"groq","fallback_used":True}), 502

    if not key:
        return groq_fallback("OPENROUTER_API_KEY is not configured")
    headers = {"Authorization":"Bearer "+key,"X-Title":"ZIRRO AI",
               "HTTP-Referer":os.getenv("APP_URL","https://github.com/emzaro731-byte/zirro")}
    try:
        result = post_json(config["url"], payload, headers, timeout=100)
        answer = result.get("choices",[{}])[0].get("message",{}).get("content","")
        if isinstance(answer,list):
            answer = "\n".join(p.get("text","") for p in answer if isinstance(p,dict))
        if not answer:
            return groq_fallback("OpenRouter returned an empty response")
        return jsonify({"reply":answer,"model":result.get("model",payload["model"]),"provider":"openrouter",
                        "fallback_used":False,
                        "web_search_used":bool(body.get("web_search") and os.getenv("TAVILY_API_KEY"))})
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode())
            error = data.get("error", {})
            detail = error.get("message", "Provider request failed") if isinstance(error,dict) else str(error)
        except Exception:
            detail = "OpenRouter request failed"
        app.logger.warning("OpenRouter HTTP %s; trying Groq fallback", exc.code)
        return groq_fallback("OpenRouter HTTP "+str(exc.code)+": "+str(detail)[:180])
    except Exception as exc:
        app.logger.warning("OpenRouter request failed (%s); trying Groq fallback", type(exc).__name__)
        return groq_fallback("OpenRouter network/request failure")

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error":"Upload too large. Keep total request under 12 MB."}), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")))
