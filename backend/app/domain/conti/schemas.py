from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.character_gen.schemas import CharacterSheet
from app.domain.cut_planner.schemas import CutPlan
from app.domain.validator.schemas import ValidationReport

OutputMode = Literal["image", "video", "mixed"]


class ContiRequest(BaseModel):
    manuscript: str = Field(..., max_length=200_000)
    genre: str
    tone: str
    output_language: str = Field(default="ko")
    output_mode: OutputMode = "image"


class GeneratedCut(BaseModel):
    cut_number: int
    image_base64: str = ""
    mime_type: str = "image/png"
    video_base64: str = ""
    video_mime_type: str = ""
    dialogue: list[str] = Field(default_factory=list)
    narration: str = Field(default="")
    description: str


class ContiResult(BaseModel):
    characters: CharacterSheet
    cuts: list[GeneratedCut]
    validation_report: ValidationReport | None = None
    reference_images: dict[str, str] = Field(default_factory=dict)


class PipelineProgress(BaseModel):
    step: int = Field(..., ge=1, le=6)
    step_name: str
    status: str = Field(..., pattern="^(running|completed|failed)$")
    detail: str | None = None


class GenerateMediaRequest(BaseModel):
    cut_plan: CutPlan
    character_sheet: CharacterSheet
    output_mode: OutputMode = "image"
    reference_images: dict[str, str] = Field(default_factory=dict)


class GenerateMediaResponse(BaseModel):
    cuts: list[GeneratedCut]
