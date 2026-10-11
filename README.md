# ZIRRO AI ✦
**Ideas become extraordinary.** A premium all-in-one AI workspace with a responsive glass-inspired UI and a Python backend.

## Included
- Responsive assistant interface with chat history stored in the browser
- AI modes: Assistant, Writer, Code Studio, Research, Image Studio and Documents
- Text conversations through OpenRouter's free-model router
- Image understanding for supported vision models; text-file attachments
- Voice dictation where the browser supports Web Speech API
- Health endpoint and Render deployment configuration

## Run locally
Python 3.10+ recommended.

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY="your-key"
# Optional: choose a model available to your account
export OPENROUTER_MODEL="openrouter/free"
python app.py
```
Open http://localhost:5000.

## Deploy free
1. Create an account at [OpenRouter](https://openrouter.ai/) and create an API key. Free model availability and quotas can change; a free account is not an unlimited service.
2. Open [Render](https://render.com/) and choose **New + → Web Service**, then connect this repository. Render can also use the included `render.yaml`.
3. Set `OPENROUTER_API_KEY` in the service's environment settings. Never place this secret in `index.html`, a public repository, or a mobile app.
4. Deploy and open your Render service URL. Check `/api/health` to see whether the key is configured.

## Important limitations
- AI answers require a valid provider key and network access.
- `openrouter/free` routes to eligible free models; provider availability, rate limits, context size, and image support vary.
- The Image Studio currently supports image analysis, not image-file generation.
- PDF uploads currently show a note instead of extracting PDF text. Text, Markdown, CSV and JSON attachments are read in the browser.
- Research mode does not have web-search tools wired in yet, so the model should not be assumed to verify live facts.
- This is a starter application. Add authentication, per-user rate limits, abuse protection and a privacy policy before opening it to the public.
