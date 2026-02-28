from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

OutputLanguage = Literal["ko", "en", "ja"]
StyleTemplate = Literal["A", "B", "C", "D"]


class MainCharacter(BaseModel):
    name: str = Field(min_length=1)
    one_line_role: str = Field(min_length=1)
    visual_keywords: str = Field(min_length=1)


class Panel(BaseModel):
    index: int = Field(ge=1, le=9)
    visual: str = Field(min_length=1)
    speech_bubbles: list[str] = Field(default_factory=list)
    narration: str | None = None

    @model_validator(mode="after")
    def _check_bubbles(self) -> "Panel":
        if len(self.speech_bubbles) > 2:
            raise ValueError("speech_bubbles must have length 0..2")
        return self


class TeaserPlan(BaseModel):
    title: str = Field(min_length=1)
    output_language: OutputLanguage
    style_template: StyleTemplate
    main_character: MainCharacter
    character_anchor_prompt: str = Field(min_length=1)
    panels: list[Panel]

    @model_validator(mode="after")
    def _check_panels(self) -> "TeaserPlan":
        if len(self.panels) != 9:
            raise ValueError("panels must have length 9")
        indices = [p.index for p in self.panels]
        if sorted(indices) != list(range(1, 10)):
            raise ValueError("panel indices must be exactly 1..9 with no duplicates")
        return self


class TeaserRequest(BaseModel):
    source_text: str = Field(min_length=1)
    output_language: OutputLanguage = "ko"
    style_template: StyleTemplate = "A"

    # Allow overrides for experiments without editing code.
    text_model: str = "gemini-3.1-pro-preview"
    image_model: str = "gemini-3.1-flash-image-preview"


class TeaserCut(BaseModel):
    index: int = Field(ge=1, le=9)
    image_base64: str = Field(min_length=1)


class TeaserResult(BaseModel):
    plan: TeaserPlan
    character_anchor_image_base64: str = Field(min_length=1)
    cuts: list[TeaserCut]

