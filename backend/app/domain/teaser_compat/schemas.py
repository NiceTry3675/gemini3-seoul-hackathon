from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.character_gen.schemas import CharacterSheet
from app.domain.conti.schemas import StyleTemplate
from app.domain.cut_planner.schemas import CutPlan


class TeaserCompatRequest(BaseModel):
    source_text: str = Field(..., min_length=1, max_length=200_000)
    output_language: str = Field(default="ko")
    style_template: StyleTemplate = "webtoon_cel"
    max_image_cuts: int = Field(default=9, ge=1, le=9)
    genre: str = Field(default="unspecified")
    tone: str = Field(default="unspecified")
    reference_images: dict[str, str] = Field(default_factory=dict)
    prompt_overrides: dict[int, str] = Field(default_factory=dict)


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
    output_language: str
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
