from fastapi import APIRouter, Depends
from google import genai

from app.shared.client import get_genai_client
from app.domain.image_generation.schemas import (
    ImageGenerationRequest,
    ImageGenerationResponse,
)
from app.domain.image_generation.service import GeminiImageService

router = APIRouter(prefix="/api/image", tags=["image-generation"])


def _get_service(client: genai.Client = Depends(get_genai_client)) -> GeminiImageService:
    return GeminiImageService(client)


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    service: GeminiImageService = Depends(_get_service),
):
    return service.generate(request)
