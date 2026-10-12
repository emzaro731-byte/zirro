# ZIRRO AI ✦

**Ideas become extraordinary.** A responsive AI workspace with a glass-inspired interface and Python/Flask backend.

## Features

- Six workspaces: Assistant, Writer, Code Studio, Research, Image Studio, and Documents.
- Chat and image understanding through OpenRouter models, subject to provider/model availability.
- Image generation through an image-output-capable OpenRouter model, when the account has the required credits.
- Optional live web search using Tavily.
- PDF text extraction for selectable-text PDFs, plus text-based attachments.
- Browser-supported voice dictation and read-aloud responses.
- Browser-local conversation history, copy controls, and a theme toggle.
- Connector marketplace with configuration status and non-billable readiness checks.
- Health endpoint and Render deployment configuration.

## Deploy on Render

1. Connect this repository to a Render Web Service.
2. Use the included `render.yaml` settings, or configure the start command as `python app.py`.
3. In the Render service's **Environment** settings, add:
   - `OPENROUTER_API_KEY` — required for AI chat and provider-backed image generation.
   - `OPENAI_API_KEY` — optional; enables ChatGPT/OpenAI API chat.
   - `XAI_API_KEY` — optional; enables Grok chat.
   - `GEMINI_API_KEY` — optional; enables Google Gemini chat.
   - `PERPLEXITY_API_KEY` — optional; enables Perplexity API chat.
   - `TAVILY_API_KEY` — optional; enables live web search.
   - `OPENROUTER_MODEL` — optional; chat model override. Default: `openrouter/free`.
   - `OPENROUTER_IMAGE_MODEL` — optional; image generation model override. Default: `google/gemini-3.1-flash-image`.
   - `OPENROUTER_EMBEDDING_MODEL` — optional; embedding model override. Default: `openai/text-embedding-3-small`.
   - `APP_URL` — optional; app URL sent as provider metadata.
4. Save the variables and deploy/redeploy.
5. Check `/api/health` and open `/connectors.html` to see configuration status and run connector checks.

**Keep all API keys in Render's environment settings. Never place secret keys in HTML, JavaScript, or a public GitHub commit.**

## API endpoints

- `GET /api/health` — basic service/configuration status.
- `GET /api/plugins` — connector catalogue and safe configuration status.
- `POST /api/plugins/<plugin_id>/test` — connector readiness test. OpenRouter and Tavily tests make a lightweight provider request; image and embedding checks only verify configuration to avoid billable generation.
- `POST /api/chat` — AI chat; supports optional web search and supported attachments.
  Send `provider` as `openrouter`, `openai`, `grok`, `gemini`, or `perplexity` to choose the configured provider.
- `POST /api/search` — run Tavily web search. JSON body: `{"query":"your search query"}`.
- `POST /api/generate-image` — image generation. JSON body: `{"prompt":"describe the image"}`.
- `POST /api/embeddings` — create embeddings. JSON body: `{"input":["first text","second text"]}`.

## Image generation costs and troubleshooting

An API key does not mean image generation is free. Image output requires a model that actually supports image generation and an OpenRouter/provider account with sufficient available credits. If you receive an insufficient-balance or credit error, review the provider's current model pricing and account balance, or choose another supported provider/model. ZIRRO reports provider hints in the chat where available; it cannot bypass provider billing or quotas.

## Daily image, video, and music limits

The migration at `supabase/migrations/20261012_daily_generation_limits.sql` creates the persistent quota table and RPC used by the Flask API. To enable the 3-per-day limit:

1. Open the Supabase project SQL Editor for project `vihbsfrwnslnmheowkhy` and run the full migration SQL from that file.
2. In Render → the ZIRRO web service → Environment, set `SUPABASE_URL=https://vihbsfrwnslnmheowkhy.supabase.co` and `SUPABASE_SERVICE_ROLE_KEY` to the project's **service_role secret key**. Keep this key server-side only; never put it in browser code or commit it to GitHub.
3. Save changes and redeploy the Render service.
4. Verify `GET /api/health` reports `supabase_quota_storage_configured: true`.

The quota is 3 image generations, 3 video generations, and 3 music generations per client per UTC day, resetting at 00:00 UTC. Generation still requires valid OpenRouter/Kie AI credentials and sufficient provider credits.

## Local development

Python 3.10+ recommended.

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY="your-key"
export OPENROUTER_MODEL="openrouter/free"
# Optional: enables web search
export TAVILY_API_KEY="your-tavily-key"
python app.py
```

Open `http://localhost:5000`.

## Current limitations

- Free-model availability, limits, and provider prices can change.
- The connector catalogue's Custom API Endpoint is a preview; arbitrary external API/OAuth integrations are not implemented by that listing alone.
- Image and embedding connector tests do not send generation/embedding requests, so they confirm configuration rather than guaranteed model availability or credit sufficiency.
- PDF extraction supports selectable text; scanned PDFs need OCR, which is not included.
- Conversation history is stored in the browser's local storage and does not sync across devices.
- Before a public multi-user launch, add authentication, per-user quotas, abuse protection, secure file handling, monitoring, and a privacy policy.
