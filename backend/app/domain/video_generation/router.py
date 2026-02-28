from __future__ import annotations

from fastapi import APIRouter, Depends
from google import genai

from app.shared.client import get_genai_client
from app.domain.video_generation.schemas import (
    VideoGenerationRequest,
    VideoGenerationResponse,
)
from app.domain.video_generation.service import GeminiVideoService

router = APIRouter(prefix="/api/video", tags=["video-generation"])


def _get_service(client: genai.Client = Depends(get_genai_client)) -> GeminiVideoService:
    return GeminiVideoService(client)


@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video(
    request: VideoGenerationRequest,
    service: GeminiVideoService = Depends(_get_service),
) -> VideoGenerationResponse:
    return await service.generate(request)
