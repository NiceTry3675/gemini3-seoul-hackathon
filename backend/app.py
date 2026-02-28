from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .teaser_models import PromptPreviewResult, TeaserRequest, TeaserResult
from .teaser_pipeline import make_client, run_prompt_preview, run_teaser
from .smoke_ui import SMOKE_UI_HTML

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


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return SMOKE_UI_HTML


@app.get("/smoke", response_class=HTMLResponse)
def smoke() -> str:
    return SMOKE_UI_HTML


@app.post("/api/teaser", response_model=TeaserResult)
def generate_teaser(req: TeaserRequest) -> TeaserResult:
    try:
        return run_teaser(_get_client(), req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/prompt-preview", response_model=PromptPreviewResult)
def prompt_preview(req: TeaserRequest) -> PromptPreviewResult:
    try:
        return run_prompt_preview(_get_client(), req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
