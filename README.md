# ZIRRO AI ✦
**Ideas become extraordinary.** A premium all-in-one AI workspace with a responsive glass-inspired UI and Python backend.

## Features
- Six AI workspaces: Assistant, Writer, Code Studio, Research, Image Studio, Documents
- Free-model routing through OpenRouter (subject to model availability and rate limits)
- Image understanding for models that accept image inputs
- PDF text extraction for text-based PDFs, plus TXT/Markdown/CSV/JSON attachments
- Optional live web search using Tavily, with search results passed to the AI
- Voice dictation in supported browsers and read-aloud responses
- Browser-local recent conversation history, copy response controls, theme toggle
- Health endpoint and Render deployment configuration

## OpenRouter embeddings
The backend includes `POST /api/embeddings` for text embeddings used in semantic search or document retrieval. It uses the same `OPENROUTER_API_KEY` as chat. The default model is `openai/text-embedding-3-small`; override it with `OPENROUTER_EMBEDDING_MODEL` if needed. Embeddings are separate from chat and do not generate images. Check the selected model’s current pricing and availability: embedding requests are not guaranteed to be free.\n\nExample request:\n```json\n{ "inputs": ["ZIRRO AI assistant", "Document search and retrieval"] }\n```\nSend that JSON to `/api/embeddings` with `Content-Type: application/json`.\n\n## Run locally\nPython 3.10+ recommended.

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY="your-key"
export OPENROUTER_MODEL="openrouter/free"
# Optional: enables live web search
export TAVILY_API_KEY="your-tavily-key"
python app.py
```
Open http://localhost:5000.

## Deploy free
1. Create an account at [OpenRouter](https://openrouter.ai/) and create an API key. Check free-model availability and limits.
2. Optional web search: create a key at [Tavily](https://tavily.com/).
3. Open [Render](https://render.com/) and create a Web Service connected to this repository. The included `render.yaml` defines the service.
4. In Render Environment, set `OPENROUTER_API_KEY`. Optionally set `TAVILY_API_KEY` for web search. Embeddings use `OPENROUTER_API_KEY`; `render.yaml` sets `OPENROUTER_EMBEDDING_MODEL`. Keep keys private; never put them in frontend files or GitHub.
5. Deploy. Open your service URL, then visit `/api/health` to check which services are configured.

## Important limitations
- The AI requires a valid provider key. Free models are not unlimited; provider quotas, supported features and availability change.
- Image Studio supports image analysis, not image generation.
- PDF extraction works for selectable text; scanned PDFs need OCR, which is not included.
- Web search is optional and requires a Tavily key. It is not enabled until configured server-side.
- Conversation history is stored in the current browser's local storage, not synced across devices or protected by user accounts.
- This starter is not yet ready for a public multi-user launch. Add authentication, per-user quotas, abuse protection, secure file handling and a privacy policy before opening it widely.
