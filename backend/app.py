from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .teaser_models import TeaserRequest, TeaserResult
from .teaser_pipeline import make_client, run_teaser

app = FastAPI(title="Teaser Studio API", version="0.1.0")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = make_client()
    return _client


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/teaser", response_model=TeaserResult)
def generate_teaser(req: TeaserRequest) -> TeaserResult:
    try:
        return run_teaser(_get_client(), req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

