from __future__ import annotations

from fastapi import APIRouter, Depends
from google import genai

from app.shared.client import get_genai_client
from app.domain.character_gen.schemas import CharacterGenRequest, CharacterGenResponse
from app.domain.character_gen.service import CharacterGenService

router = APIRouter(prefix="/api/pipeline", tags=["character-gen"])


def _get_service(client: genai.Client = Depends(get_genai_client)) -> CharacterGenService:
    return CharacterGenService(client)


@router.post("/character-gen", response_model=CharacterGenResponse)
async def character_gen(
    request: CharacterGenRequest,
    service: CharacterGenService = Depends(_get_service),
) -> CharacterGenResponse:
    return service.generate(request)
