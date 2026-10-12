import base64, io, json, os, sqlite3, hashlib, urllib.request, urllib.error
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
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "chat_failover": False,
        "image_generation_configured": bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("KIE_AI_API_KEY")),
        "video_generation_configured": bool(os.getenv("KIE_AI_API_KEY")),
        "video_model": "runway",
        "music_generation_configured": bool(os.getenv("KIE_AI_API_KEY")),
        "music_provider": "Kie AI / Suno",
        "image_model": os.getenv("OPENROUTER_IMAGE_MODEL", "google/gemini-3.1-flash-image") + " (Kie AI fallback enabled)",
        "web_search_configured": bool(os.getenv("TAVILY_API_KEY")),
        "embeddings_configured": bool(os.getenv("OPENROUTER_API_KEY")),
        "embedding_model": os.getenv("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small"),
        "pdf_support": True, "image_upload": True, "video_upload": "sampled_frames", "text_file_upload": True})


PLUGIN_CATALOG = [
    {"id": "openrouter", "name": "OpenRouter AI", "type": "connector", "feature": "chat", "env": "OPENROUTER_API_KEY"},
    {"id": "openai", "name": "ChatGPT / OpenAI", "type": "connector", "feature": "chat", "env": "OPENAI_API_KEY"},
    {"id": "groq", "name": "Groq", "type": "connector", "feature": "chat", "env": "GROQ_API_KEY"},
    {"id": "gemini", "name": "Google Gemini", "type": "connector", "feature": "chat", "env": "GEMINI_API_KEY"},
    {"id": "perplexity", "name": "Perplexity AI", "type": "connector", "feature": "chat", "env": "PERPLEXITY_API_KEY"},
    {"id": "tavily", "name": "Tavily Web Search", "type": "connector", "feature": "search", "env": "TAVILY_API_KEY"},
    {"id": "imagegen", "name": "Image Generation", "type": "plugin", "feature": "image", "env": "KIE_AI_API_KEY"},
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
        "groq": bool(os.getenv("SUPABASE_URL") and os.getenv("ZIRRO_SUPABASE_PROXY_TOKEN")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "perplexity": bool(os.getenv("PERPLEXITY_API_KEY")),
        "tavily": bool(os.getenv("TAVILY_API_KEY")),
        "imagegen": bool(os.getenv("OPENROUTER_API_KEY") or os.getenv("KIE_AI_API_KEY")),
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
                "gemini": ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai/models", "Google Gemini"),
        "perplexity": ("PERPLEXITY_API_KEY", "https://api.perplexity.ai/chat/completions", "Perplexity AI"),
    }
    if plugin_id == "groq":
        token = os.getenv("GROQ_API_KEY", "").strip()
        if not token:
            return jsonify({"ok": False, "status": "needs_setup", "message": "Set GROQ_API_KEY in Render Environment, then redeploy."}), 503
        try:
            req = urllib.request.Request("https://api.groq.com/openai/v1/models", headers={"Authorization": "Bearer " + token})
            with urllib.request.urlopen(req, timeout=20) as response:
                if response.status == 200:
                    return jsonify({"ok": True, "status": "connected", "message": "Groq API responded successfully."})
        except urllib.error.HTTPError as exc:
            return jsonify({"ok": False, "status": "error", "message": "Groq returned HTTP " + str(exc.code) + ". Check the API key, model access, and account limits."}), 502
        except Exception:
            return jsonify({"ok": False, "status": "error", "message": "Could not reach Groq. Try again shortly."}), 502
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


GENERATION_DAILY_LIMIT = 3
GENERATION_DB = os.getenv("GENERATION_LIMIT_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "zirro_generation_limits.sqlite3"))

def _check_generation_limit(kind, body):
    client_id = str((body or {}).get("client_id", "")).strip()
    if not (12 <= len(client_id) <= 100 and all(c.isalnum() or c in "-_." for c in client_id)):
        forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        client_id = "ip:" + (forwarded or request.remote_addr or "unknown")
    key = hashlib.sha256((kind + ":" + client_id).encode()).hexdigest()
    from datetime import datetime, timezone
    day = datetime.now(timezone.utc).date().isoformat()
    try:
        with sqlite3.connect(GENERATION_DB, timeout=10) as db:
            db.execute("CREATE TABLE IF NOT EXISTS generation_daily_usage (day TEXT NOT NULL, kind TEXT NOT NULL, client_key TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(day, kind, client_key))")
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT used FROM generation_daily_usage WHERE day=? AND kind=? AND client_key=?", (day, kind, key)).fetchone()
            used = int(row[0]) if row else 0
            if used >= 3:
                db.rollback()
                return False, {"ok": False, "error": f"Daily limit reached: 3 {kind} generations per day. Try again after 00:00 UTC.", "limit": 3, "used": used, "remaining": 0, "resets_at": "00:00 UTC"}
            if row:
                db.execute("UPDATE generation_daily_usage SET used=used+1 WHERE day=? AND kind=? AND client_key=?", (day, kind, key))
            else:
                db.execute("INSERT INTO generation_daily_usage(day,kind,client_key,used) VALUES(?,?,?,1)", (day, kind, key))
            db.commit()
            return True, {"limit": 3, "used": used + 1, "remaining": 2 - used, "resets_at": "00:00 UTC"}
    except sqlite3.Error:
        app.logger.exception("Generation limit storage error")
        return False, {"ok": False, "error": "Could not verify the daily generation limit. Please try again shortly."}

def _provider_error(exc, fallback):
    try:
        data = json.loads(exc.read().decode())
        error = data.get("error", data)
        if isinstance(error, dict):
            return str(error.get("message") or error.get("detail") or fallback)[:500]
        return str(error)[:500]
    except Exception:
        return fallback


def _kie_key():
    return os.getenv("KIE_AI_API_KEY", "").strip()


def _kie_request(path, payload=None, timeout=45):
    token = _kie_key()
    if not token:
        raise RuntimeError("Add KIE_AI_API_KEY to Render Environment, then redeploy.")
    url = "https://api.kie.ai" + path
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    if payload is None:
        req = urllib.request.Request(url, headers=headers, method="GET")
    else:
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        result = json.loads(response.read().decode())
    if isinstance(result, dict) and result.get("code") not in (None, 0, 200):
        raise RuntimeError(str(result.get("msg") or result.get("message") or "Kie AI request failed")[:400])
    return result


def _kie_create_task(model, task_input, timeout=45):
    result = _kie_request("/api/v1/jobs/createTask", {
        "model": model,
        "input": task_input
    }, timeout=timeout)
    data = result.get("data") or {}
    task_id = data.get("taskId") or data.get("task_id") or result.get("taskId")
    if not task_id:
        raise RuntimeError(str(result.get("msg") or "Kie AI did not return a task ID.")[:350])
    return str(task_id)


def _kie_task(task_id):
    from urllib.parse import urlencode
    result = _kie_request("/api/v1/jobs/recordInfo?" + urlencode({"taskId": task_id}), timeout=30)
    data = result.get("data") or {}
    raw = data.get("resultJson") or data.get("result_json") or "{}"
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {}
    else:
        parsed = raw if isinstance(raw, dict) else {}
    urls = parsed.get("resultUrls") or parsed.get("result_urls") or []
    if isinstance(urls, str):
        urls = [urls]
    response_data = (data.get("response") or {}).get("data") if isinstance(data.get("response"), dict) else None
    if isinstance(response_data, list):
        for item in response_data:
            if isinstance(item, dict):
                url = item.get("audio_url") or item.get("video_url") or item.get("image_url") or item.get("url")
                if url:
                    urls.append(url)
    if not urls:
        for key in ("video_url", "audio_url", "image_url", "url"):
            if parsed.get(key):
                urls.append(parsed[key])
    return {
        "task_id": str(data.get("taskId") or task_id),
        "status": str(data.get("state") or data.get("status") or "unknown").lower(),
        "urls": [u for u in urls if isinstance(u, str) and u.startswith(("https://", "http://"))],
        "error": data.get("failMsg") or data.get("error"),
        "model": data.get("model"),
        "credits_consumed": data.get("creditsConsumed")
    }


def _kie_wait_for_result(task_id, attempts=35, delay=2):
    import time
    latest = {"task_id": task_id, "status": "waiting", "urls": []}
    for _ in range(attempts):
        latest = _kie_task(task_id)
        if latest["status"] == "success" and latest["urls"]:
            return latest
        if latest["status"] in ("fail", "failed", "error", "cancelled", "canceled"):
            raise RuntimeError(str(latest.get("error") or "Kie AI generation failed.")[:400])
        time.sleep(delay)
    return latest


@app.post("/api/generate-image")
def generate_image():
    """Try OpenRouter image generation first, then fall back to Kie AI."""
    body = request.get_json(silent=True) or {}
    allowed, quota = _check_generation_limit("image", body)
    if not allowed:
        return jsonify(quota), 429
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"error": "Describe the image you want to create."}), 400
    if len(prompt) > 4000:
        return jsonify({"error": "Prompt is too long (maximum 4,000 characters)."}), 413

    openrouter_error = "OpenRouter image generation is not configured."
    token = str(body.get("api_key", "")).strip() or os.getenv("OPENROUTER_API_KEY", "").strip()
    if token:
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
            }, timeout=90)
            message = result.get("choices", [{}])[0].get("message", {})
            images = message.get("images") or []
            image_url = (images[0].get("image_url") or {}).get("url") if images and isinstance(images[0], dict) else None
            if not image_url and isinstance(message.get("content"), list):
                for part in message["content"]:
                    if isinstance(part, dict) and part.get("type") in ("image_url", "image"):
                        image_url = (part.get("image_url") or {}).get("url") or part.get("url")
                        if image_url:
                            break
            if isinstance(image_url, str) and image_url.startswith(("data:image/", "https://", "http://")):
                return jsonify({"ok": True, "image": image_url, "model": result.get("model", model), "provider": "OpenRouter", "fallback_used": False})
            openrouter_error = "OpenRouter did not return an image. " + str(message.get("content", ""))[:180]
        except urllib.error.HTTPError as exc:
            openrouter_error = "OpenRouter error: " + _provider_error(exc, "Image generation request failed.")
        except Exception as exc:
            app.logger.warning("OpenRouter image generation failed; trying Kie AI: %s", exc)
            openrouter_error = str(exc)[:250]

    if not _kie_key():
        return jsonify({"error": openrouter_error, "hint": "Add KIE_AI_API_KEY in Render Environment to enable automatic Kie AI fallback."}), 502
    try:
        task_id = _kie_create_task("gpt-image-2-text-to-image", {
            "prompt": prompt,
            "aspect_ratio": str(body.get("aspect_ratio") or "auto")
        })
        result = _kie_wait_for_result(task_id, attempts=40, delay=2)
        if result["status"] == "success" and result["urls"]:
            return jsonify({"ok": True, "image": result["urls"][0], "model": "gpt-image-2-text-to-image", "provider": "Kie AI", "fallback_used": True, "task_id": task_id})
        return jsonify({"ok": False, "error": "Kie AI accepted the image job but it is still processing.", "task_id": task_id, "provider": "Kie AI", "fallback_used": True}), 202
    except urllib.error.HTTPError as exc:
        return jsonify({"error": openrouter_error, "fallback_error": _provider_error(exc, "Kie AI image generation failed.")}), 502
    except Exception as exc:
        app.logger.exception("Kie AI image fallback failed")
        return jsonify({"error": openrouter_error, "fallback_error": str(exc)[:350], "hint": "Check KIE_AI_API_KEY, Kie AI credits, and the selected model's availability."}), 502


@app.get("/api/image/status/<task_id>")
def image_status(task_id):
    if not task_id or len(task_id) > 180 or not all(c.isalnum() or c in "-_." for c in task_id):
        return jsonify({"ok": False, "error": "Invalid image task ID."}), 400
    try:
        task = _kie_task(task_id)
        return jsonify({"ok": True, "task_id": task_id, "status": task["status"],
                        "image_url": task["urls"][0] if task["urls"] else None,
                        "error": task["error"], "provider": "Kie AI"})
    except urllib.error.HTTPError as exc:
        return jsonify({"ok": False, "error": _provider_error(exc, "Could not read Kie AI image status.")}), 502
    except Exception as exc:
        app.logger.exception("Kie AI image status check failed")
        return jsonify({"ok": False, "error": str(exc)[:350]}), 502


@app.get("/api/video/models")
def video_models():
    if not _kie_key():
        return jsonify({"ok": False, "error": "Configure KIE_AI_API_KEY in Render to enable video generation."}), 503
    return jsonify({"ok": True, "provider": "Kie AI", "models": [
        {"id": "runway", "name": "Runway", "supported_durations": [5, 10], "supported_resolutions": ["720p", "1080p"], "supported_aspect_ratios": ["16:9", "9:16"]}
    ]})


@app.post("/api/generate-video")
def generate_video():
    body = request.get_json(silent=True) or {}
    allowed, quota = _check_generation_limit("video", body)
    if not allowed:
        return jsonify(quota), 429
    if not _kie_key():
        return jsonify({"ok": False, "error": "Add KIE_AI_API_KEY in Render Environment, then redeploy."}), 503
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"ok": False, "error": "Describe the video you want to create."}), 400
    if len(prompt) > 4000:
        return jsonify({"ok": False, "error": "Prompt must be 4,000 characters or fewer."}), 413
    duration = 10 if str(body.get("duration", 5)) == "10" else 5
    resolution = str(body.get("resolution", "720p"))
    if resolution not in ("720p", "1080p"):
        resolution = "720p"
    if duration == 10:
        resolution = "720p"
    aspect_ratio = str(body.get("aspect_ratio", "16:9"))
    if aspect_ratio not in ("16:9", "9:16"):
        aspect_ratio = "16:9"
    task_input = {"prompt": prompt, "duration": duration, "quality": resolution,
                  "aspect_ratio": aspect_ratio, "watermark": ""}
    try:
        task_id = _kie_create_task("runway", task_input, timeout=60)
        return jsonify({"ok": True, "job_id": task_id, "status": "waiting", "model": "runway",
                        "provider": "Kie AI", "message": "Kie AI video job submitted. Generation may take several minutes and may use credits."}), 202
    except urllib.error.HTTPError as exc:
        detail = _provider_error(exc, "Kie AI video generation failed.")
        status = 402 if exc.code == 402 or any(w in detail.lower() for w in ("balance", "credit", "insufficient")) else 502
        return jsonify({"ok": False, "error": detail, "hint": "Check your Kie AI key, credits, and model requirements."}), status
    except Exception as exc:
        app.logger.exception("Kie AI video generation request failed")
        return jsonify({"ok": False, "error": str(exc)[:350]}), 502


@app.get("/api/video/status/<job_id>")
def video_status(job_id):
    if not job_id or len(job_id) > 180 or not all(c.isalnum() or c in "-_." for c in job_id):
        return jsonify({"ok": False, "error": "Invalid video job ID."}), 400
    try:
        task = _kie_task(job_id)
        return jsonify({"ok": True, "job_id": job_id, "status": task["status"],
                        "error": task["error"], "video_url": task["urls"][0] if task["urls"] else None,
                        "provider": "Kie AI", "credits_consumed": task["credits_consumed"]})
    except urllib.error.HTTPError as exc:
        return jsonify({"ok": False, "error": _provider_error(exc, "Could not read Kie AI video status.")}), 502
    except Exception as exc:
        app.logger.exception("Kie AI video status check failed")
        return jsonify({"ok": False, "error": str(exc)[:350]}), 502


@app.post("/api/generate-music")
def generate_music():
    body = request.get_json(silent=True) or {}
    allowed, quota = _check_generation_limit("music", body)
    if not allowed:
        return jsonify(quota), 429
    if not _kie_key():
        return jsonify({"ok": False, "error": "Add KIE_AI_API_KEY in Render Environment, then redeploy."}), 503
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        return jsonify({"ok": False, "error": "Describe the music you want to create."}), 400
    if len(prompt) > 2000:
        return jsonify({"ok": False, "error": "Music prompt must be 2,000 characters or fewer."}), 413
    try:
        duration = max(10, min(int(body.get("duration", 30)), 60))
    except (TypeError, ValueError):
        duration = 30
    title = str(body.get("title") or prompt[:70]).strip()[:80] or "ZIRRO AI Music"
    task_input = {"custom_mode": True, "instrumental": True, "model": "V6",
                  "style": prompt[:1000], "title": title, "duration": duration}
    try:
        task_id = _kie_create_task("ai-music-api/generate", task_input, timeout=60)
        return jsonify({"ok": True, "prediction_id": task_id, "status": "waiting",
                        "message": "Suno music job submitted through Kie AI. It may use credits."}), 202
    except urllib.error.HTTPError as exc:
        return jsonify({"ok": False, "error": _provider_error(exc, "Kie AI music generation failed."),
                        "hint": "Check KIE_AI_API_KEY, Kie AI credits, and Suno model availability."}), 502
    except Exception as exc:
        app.logger.exception("Kie AI music generation request failed")
        return jsonify({"ok": False, "error": str(exc)[:350]}), 502


@app.get("/api/music/status/<prediction_id>")
def music_status(prediction_id):
    if not prediction_id or len(prediction_id) > 180 or not all(c.isalnum() or c in "-_." for c in prediction_id):
        return jsonify({"ok": False, "error": "Invalid music task ID."}), 400
    try:
        task = _kie_task(prediction_id)
        return jsonify({"ok": True, "prediction_id": prediction_id, "status": task["status"],
                        "music_url": task["urls"][0] if task["urls"] else None,
                        "error": task["error"], "provider": "Kie AI",
                        "credits_consumed": task["credits_consumed"]})
    except urllib.error.HTTPError as exc:
        return jsonify({"ok": False, "error": _provider_error(exc, "Could not read Kie AI music status.")}), 502
    except Exception as exc:
        app.logger.exception("Kie AI music status check failed")
        return jsonify({"ok": False, "error": str(exc)[:350]}), 502


@app.post("/api/chat")
def chat():
    body = request.get_json(silent=True) or {}
    provider = str(body.get("provider", "openrouter")).lower()
    providers = {
        "openrouter": {"env":"OPENROUTER_API_KEY","url":"https://openrouter.ai/api/v1/chat/completions","model":os.getenv("OPENROUTER_MODEL","openrouter/free"),"name":"ZIRRO AI"},
        "groq": {"env":"GROQ_API_KEY","url":"https://api.groq.com/openai/v1/chat/completions","model":os.getenv("GROQ_MODEL","llama-3.3-70b-versatile"),"name":"Groq"}
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
    if not key:
        return jsonify({"error":"Add "+config["env"]+" in Render Environment, then redeploy."}), 503
    headers = {"Authorization":"Bearer "+key,"X-Title":"ZIRRO AI",
               "HTTP-Referer":os.getenv("APP_URL","https://github.com/emzaro731-byte/zirro")}
    try:
        result = post_json(config["url"], payload, headers, timeout=100)
        answer = result.get("choices",[{}])[0].get("message",{}).get("content","")
        if isinstance(answer,list):
            answer = "\n".join(p.get("text","") for p in answer if isinstance(p,dict))
        if not answer:
            return jsonify({"error":config["name"]+" returned an empty response.","provider":provider}), 502
        return jsonify({"reply":answer,"model":result.get("model",payload["model"]),"provider":provider,
                        "fallback_used":False,
                        "web_search_used":bool(body.get("web_search") and os.getenv("TAVILY_API_KEY"))})
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read().decode())
            error = data.get("error", {})
            detail = error.get("message", "Provider request failed") if isinstance(error,dict) else str(error)
        except Exception:
            detail = config["name"]+" request failed"
        return jsonify({"error":config["name"]+" API error: "+str(detail)[:300],"provider":provider}), 502
    except Exception:
        app.logger.exception(config["name"]+" request failed")
        return jsonify({"error":"Could not reach "+config["name"]+". Check the API key and try again.","provider":provider}), 502


@app.post("/api/provider-proxy")
def provider_proxy():
    """Forward a constrained provider request to Supabase; provider keys never reach this app."""
    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    proxy_token = os.getenv("ZIRRO_SUPABASE_PROXY_TOKEN", "").strip()
    if not supabase_url or not proxy_token:
        return jsonify({"ok": False, "error": "Configure SUPABASE_URL and ZIRRO_SUPABASE_PROXY_TOKEN in Render Environment."}), 503
    body = request.get_json(silent=True) or {}
    provider = str(body.get("provider", "")).lower()
    path = str(body.get("path", ""))
    method = str(body.get("method", "POST")).upper()
    if provider not in ("fal", "kie"):
        return jsonify({"ok": False, "error": "Provider must be fal or kie."}), 400
    if method not in ("GET", "POST"):
        return jsonify({"ok": False, "error": "Only GET and POST are supported."}), 400
    if not path or len(path) > 500 or ".." in path or "://" in path:
        return jsonify({"ok": False, "error": "Invalid provider path."}), 400
    payload = {"provider": provider, "path": path, "method": method, "body": body.get("body", {})}
    try:
        result = post_json(supabase_url + "/functions/v1/zirro-provider-proxy", payload,
            {"x-zirro-proxy-token": proxy_token}, timeout=115)
        return jsonify(result)
    except urllib.error.HTTPError as exc:
        detail = _provider_error(exc, "Supabase provider proxy request failed.")
        return jsonify({"ok": False, "error": detail}), exc.code if exc.code in (400, 401, 404, 429, 503) else 502
    except Exception:
        app.logger.exception("Supabase provider proxy request failed")
        return jsonify({"ok": False, "error": "Could not reach the Supabase provider proxy."}), 502

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error":"Upload too large. Keep total request under 12 MB."}), 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","5000")))
