from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.scene_parser.schemas import NovelInput, SceneBreakdown
from app.domain.character_gen.schemas import CharacterSheet


class CutPlanRequest(BaseModel):
    novel_input: NovelInput
    scene_breakdown: SceneBreakdown
    character_sheet: CharacterSheet


class Cut(BaseModel):
    cut_number: int = Field(..., ge=1, le=12)
    scene_ref: int = Field(..., ge=1)
    description: str
    dialogue: list[str] = Field(default_factory=list)
    narration: str = Field(default="")
    camera_angle: str
    emotion: str
    image_prompt: str


class CutPlan(BaseModel):
    cuts: list[Cut] = Field(..., min_length=12, max_length=12)
