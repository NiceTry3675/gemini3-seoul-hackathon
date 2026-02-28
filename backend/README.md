# Backend

## Setup

1. Create venv (repo root):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. Set API key:

- Put `GOOGLE_API_KEY=...` (or `GEMINI_API_KEY=...`) in `.env`, or export it in your shell.

## Run

From repo root:

```bash
source .venv/bin/activate
uvicorn backend.app:app --reload --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/healthz
```

Smoke UI (prompt preview + image generation):

```bash
open http://127.0.0.1:8000/smoke
```

Prompt preview API:

```bash
curl -X POST http://127.0.0.1:8000/api/prompt-preview \
  -H 'Content-Type: application/json' \
  -d '{
    "source_text": "여기에 소설 초반 텍스트를 넣으세요",
    "output_language": "ko",
    "style_template": "A"
  }'
```

Generate teaser (returns plan + anchor image + 9 cuts as base64 PNG):

```bash
curl -X POST http://127.0.0.1:8000/api/teaser \
  -H 'Content-Type: application/json' \
  -d '{
    "source_text": "여기에 소설 초반 텍스트를 넣으세요",
    "output_language": "ko",
    "style_template": "A",
    "max_image_cuts": 9
  }'
```

Notes:

- `/api/teaser` is sequential (`anchor + cuts`) so full 9 cuts can take time.
- For smoke tests, use a smaller `max_image_cuts` (for example 1~3).
- Generated images are saved under `outputs/teaser_<timestamp>_<id>/`
  with files: `anchor.png`, `cut_01.png...`, and `plan.json`.
- If you see SSL timeout errors (for example `_ssl.c:983: The handshake operation timed out`),
  retry once and check outbound network/proxy settings. The backend now retries transient network failures.
- Do not set very short request deadlines; Gemini Developer API rejects deadlines under 10 seconds.
- This project uses default `genai.Client()` transport settings and app-level retry logic.
