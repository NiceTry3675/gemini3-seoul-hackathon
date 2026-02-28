from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse
from google import genai

from app.shared.client import get_genai_client
from app.domain.text_generation.schemas import (
    TextGenerationRequest,
    TextGenerationResponse,
    StructuredGenerationRequest,
)
from app.domain.text_generation.service import GeminiTextService

router = APIRouter(prefix="/api/text", tags=["text-generation"])


def _get_service(client: genai.Client = Depends(get_genai_client)) -> GeminiTextService:
    return GeminiTextService(client)


@router.post("/generate", response_model=TextGenerationResponse)
async def generate_text(
    request: TextGenerationRequest,
    service: GeminiTextService = Depends(_get_service),
):
    return service.generate(request)


@router.post("/structured")
async def generate_structured(
    request: StructuredGenerationRequest,
    service: GeminiTextService = Depends(_get_service),
):
    return service.generate_structured(request)


@router.post("/stream")
async def generate_stream(
    request: TextGenerationRequest,
    service: GeminiTextService = Depends(_get_service),
):
    return EventSourceResponse(service.generate_stream(request))
