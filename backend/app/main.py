from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.exceptions import DomainException
from app.shared.database import init_db
from app.shared.client import get_genai_client
from app.routers.health import router as health_router
from app.domain.text_generation.router import router as text_router
from app.domain.image_generation.router import router as image_router
from app.domain.scene_parser.router import router as scene_parser_router
from app.domain.character_gen.router import router as character_gen_router
from app.domain.cut_planner.router import router as cut_planner_router
from app.domain.validator.router import router as validator_router
from app.domain.conti.router import router as conti_router
from app.domain.conti.schemas import ContiRequest, PromptPreviewResult
from app.domain.conti.service import ContiOrchestratorService
from app.domain.video_generation.router import router as video_router
from app.domain.teaser.router import router as teaser_router
from app.domain.style_preview.router import router as style_preview_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Gemini API Wrapper",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin", "*")
    return {
        "access-control-allow-origin": origin,
        "access-control-allow-credentials": "true",
    }


@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        headers=_cors_headers(request),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import logging
    logging.getLogger(__name__).exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
        headers=_cors_headers(request),
    )


# Routers - health is always included
app.include_router(health_router)

# Domain routers
app.include_router(text_router)
app.include_router(image_router)
app.include_router(scene_parser_router)
app.include_router(character_gen_router)
app.include_router(cut_planner_router)
app.include_router(validator_router)
app.include_router(conti_router)
app.include_router(video_router)
app.include_router(teaser_router)
app.include_router(style_preview_router)


class LegacyPromptPreviewRequest(BaseModel):
    source_text: str
    style_template: str = "webtoon_cel"
    output_language: str = "ko"
    output_mode: str = "image"
    genre: str = ""
    tone: str = ""


@app.post("/api/prompt-preview", response_model=PromptPreviewResult)
async def prompt_preview_legacy(request: LegacyPromptPreviewRequest):
    service = ContiOrchestratorService(get_genai_client())
    conti_request = ContiRequest(
        manuscript=request.source_text,
        genre=request.genre,
        tone=request.tone,
        output_language=request.output_language,
        output_mode=request.output_mode,
        style_template=request.style_template,
    )
    return await service.preview(conti_request)
