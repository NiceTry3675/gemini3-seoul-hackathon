from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.character_gen.schemas import CharacterSheet
from app.domain.cut_planner.schemas import CutPlan
from app.domain.validator.schemas import ValidationReport

OutputMode = Literal["image", "video", "mixed"]
StyleTemplate = Literal["webtoon_cel", "cinematic_realism", "watercolor_dream", "digital_masterpaint"]


class ContiRequest(BaseModel):
    manuscript: str = Field(..., max_length=200_000)
    genre: str
    tone: str
    output_language: str = Field(default="ko")
    output_mode: OutputMode = "image"
    style_template: StyleTemplate = "webtoon_cel"


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
    style_template: StyleTemplate = "webtoon_cel"
    reference_images: dict[str, str] = Field(default_factory=dict)


class GenerateMediaResponse(BaseModel):
    cuts: list[GeneratedCut]


class PromptPreviewCut(BaseModel):
    cut_number: int
    styled_prompt: str
    reference_inputs: list[str]


class PromptPreviewResult(BaseModel):
    cut_plan: CutPlan
    characters: CharacterSheet
    anchor_prompt: str
    cuts: list[PromptPreviewCut]


class RunSummary(BaseModel):
    id: str
    manuscript_preview: str
    genre: str
    tone: str
    output_mode: OutputMode = "image"
    status: str
    cut_count: int
    started_at: str
    finished_at: str | None = None


class RunDetail(BaseModel):
    id: str
    manuscript: str
    genre: str
    tone: str
    output_language: str
    output_mode: OutputMode = "image"
    status: str
    characters: CharacterSheet | None = None
    cuts: list[GeneratedCut] = Field(default_factory=list)
    validation_report: ValidationReport | None = None
    steps: list[PipelineProgress] = Field(default_factory=list)
    error_detail: str | None = None
    started_at: str
    finished_at: str | None = None
