from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.character_gen.schemas import CharacterSheet
from app.domain.validator.schemas import ValidationReport


class ContiRequest(BaseModel):
    manuscript: str = Field(..., max_length=200_000)
    genre: str
    tone: str
    output_language: str = Field(default="ko")


class GeneratedCut(BaseModel):
    cut_number: int
    image_base64: str
    mime_type: str
    dialogue: list[str] = Field(default_factory=list)
    narration: str = Field(default="")
    description: str


class ContiResult(BaseModel):
    characters: CharacterSheet
    cuts: list[GeneratedCut]
    validation_report: ValidationReport | None = None


class PipelineProgress(BaseModel):
    step: int = Field(..., ge=1, le=5)
    step_name: str
    status: str = Field(..., pattern="^(running|completed|failed)$")
    detail: str | None = None
