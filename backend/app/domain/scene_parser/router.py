from __future__ import annotations

from fastapi import APIRouter, Depends
from google import genai

from app.shared.client import get_genai_client
from app.domain.scene_parser.schemas import NovelInput, SceneBreakdown
from app.domain.scene_parser.service import SceneParserService

router = APIRouter(prefix="/api/pipeline", tags=["scene-parser"])


def _get_service(client: genai.Client = Depends(get_genai_client)) -> SceneParserService:
    return SceneParserService(client)


@router.post("/scene-parse", response_model=SceneBreakdown)
async def scene_parse(
    request: NovelInput,
    service: SceneParserService = Depends(_get_service),
) -> SceneBreakdown:
    return await service.parse(request)
