from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.character_gen.schemas import CharacterSheet
from app.domain.conti.schemas import StyleTemplate
from app.domain.cut_planner.schemas import CutPlan

TeaserLanguage = Literal["ko", "en", "ja"]


class TeaserCompatRequest(BaseModel):
    source_text: str = Field(..., min_length=1, max_length=200_000)
    output_language: TeaserLanguage = "ko"
    style_template: StyleTemplate = "webtoon_cel"
    max_image_cuts: int = Field(default=9, ge=1, le=9)
    genre: str = Field(default="unspecified")
    tone: str = Field(default="unspecified")
    reference_images: dict[str, str] = Field(default_factory=dict)
    prompt_overrides: dict[int, str] = Field(default_factory=dict)
    translate_to_language: TeaserLanguage | None = None


class MainCharacterCompat(BaseModel):
    name: str
    one_line_role: str
    visual_keywords: str


class PanelCompat(BaseModel):
    index: int = Field(..., ge=1, le=9)
    visual: str
    speech_bubbles: list[str] = Field(default_factory=list)
    narration: str | None = None


class TeaserPlanCompat(BaseModel):
    title: str
    output_language: TeaserLanguage
    style_template: StyleTemplate
    main_character: MainCharacterCompat
    character_anchor_prompt: str
    panels: list[PanelCompat]


class PromptPreviewCutCompat(BaseModel):
    index: int = Field(..., ge=1, le=9)
    prompt: str
    reference_inputs: list[str] = Field(default_factory=list)


class PromptPreviewCompatResponse(BaseModel):
    plan: TeaserPlanCompat
    anchor_prompt: str
    cuts: list[PromptPreviewCutCompat]
    cut_plan: CutPlan
    character_sheet: CharacterSheet


class TeaserCutCompat(BaseModel):
    index: int = Field(..., ge=1, le=9)
    image_base64: str = Field(default="")


class TeaserCompatResponse(BaseModel):
    plan: TeaserPlanCompat
    character_anchor_image_base64: str = Field(default="")
    cuts: list[TeaserCutCompat]
    translated_to_language: TeaserLanguage | None = None
    export_run_id: str | None = None


class TeaserTranslateCut(BaseModel):
    index: int = Field(..., ge=1, le=9)
    image_base64: str = Field(default="")
    mime_type: str = Field(default="image/png")
    dialogue: list[str] = Field(default_factory=list)
    narration: str = Field(default="")
    description: str = Field(default="")


class TeaserTranslateRequest(BaseModel):
    source_language: TeaserLanguage = "ko"
    target_language: TeaserLanguage
    cuts: list[TeaserTranslateCut] = Field(..., min_length=1, max_length=9)


class TeaserTranslateResponse(BaseModel):
    translated_to_language: TeaserLanguage
    cuts: list[TeaserCutCompat]
    export_run_id: str | None = None
