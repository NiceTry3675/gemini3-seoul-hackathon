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

Generate teaser (returns plan + anchor image + 9 cuts as base64 PNG):

```bash
curl -X POST http://127.0.0.1:8000/api/teaser \
  -H 'Content-Type: application/json' \
  -d '{
    "source_text": "여기에 소설 초반 텍스트를 넣으세요",
    "output_language": "ko",
    "style_template": "A"
  }'
```
