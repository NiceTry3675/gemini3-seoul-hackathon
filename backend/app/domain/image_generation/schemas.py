from __future__ import annotations
from pydantic import BaseModel


class ImageGenerationRequest(BaseModel):
    prompt: str
    system_instruction_key: str | None = None
    reference_images: dict[str, str] = {}  # name → base64


class ImageGenerationResponse(BaseModel):
    image_base64: str
    mime_type: str
