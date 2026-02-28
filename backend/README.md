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
cd backend
uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Pipeline generate API (SSE stream):

```bash
curl -N -X POST http://127.0.0.1:8000/api/pipeline/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "manuscript": "여기에 소설 초반 텍스트를 넣으세요",
    "genre": "fantasy",
    "tone": "mysterious",
    "output_language": "ko",
    "output_mode": "image",
    "style_template": "webtoon_cel"
  }'
```

Pipeline prompt preview API:

```bash
curl -X POST http://127.0.0.1:8000/api/pipeline/preview \
  -H 'Content-Type: application/json' \
  -d '{
    "manuscript": "여기에 소설 초반 텍스트를 넣으세요",
    "genre": "fantasy",
    "tone": "mysterious",
    "output_language": "ko",
    "output_mode": "image",
    "style_template": "webtoon_cel"
  }'
```

Run history APIs:

```bash
curl http://127.0.0.1:8000/api/pipeline/runs
curl http://127.0.0.1:8000/api/pipeline/runs/<run_id>
```

Notes:

- `/api/pipeline/generate` is sequential (`anchor + cuts`) so full 9 cuts can take time.
- Prompt templates and system instructions are managed in `backend/system_instruction.toml`.
- If you see SSL timeout errors (for example `_ssl.c:983: The handshake operation timed out`),
  retry once and check outbound network/proxy settings. The backend now retries transient network failures.
- Do not set very short request deadlines; Gemini Developer API rejects deadlines under 10 seconds.
- This project uses default `genai.Client()` transport settings and app-level retry logic.
