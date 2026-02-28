from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.exceptions import DomainException
from app.shared.database import init_db
from app.routers.health import router as health_router
from app.domain.text_generation.router import router as text_router
from app.domain.image_generation.router import router as image_router
from app.domain.scene_parser.router import router as scene_parser_router
from app.domain.character_gen.router import router as character_gen_router
from app.domain.cut_planner.router import router as cut_planner_router
from app.domain.validator.router import router as validator_router
from app.domain.conti.router import router as conti_router
from app.domain.video_generation.router import router as video_router

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


@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
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
