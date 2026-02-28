from __future__ import annotations
from pydantic import BaseModel, Field


class MultimodalPart(BaseModel):
    """Base64로 인코딩된 멀티모달 데이터."""
    data: str
    mime_type: str


class TextGenerationRequest(BaseModel):
    prompt: str
    parts: list[MultimodalPart] = []
    system_instruction_key: str | None = None
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=8192, ge=1, le=65536)


class StructuredGenerationRequest(TextGenerationRequest):
    response_schema: dict  # JSON Schema dict


class TextGenerationResponse(BaseModel):
    text: str
    usage_metadata: dict | None = None
