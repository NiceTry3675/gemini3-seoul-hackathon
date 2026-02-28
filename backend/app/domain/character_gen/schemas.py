from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.scene_parser.schemas import NovelInput, SceneBreakdown


class CharacterGenRequest(BaseModel):
    novel_input: NovelInput
    scene_breakdown: SceneBreakdown


class Character(BaseModel):
    name: str
    appearance: str
    personality: str
    role: str
    visual_prompt: str


class CharacterSheet(BaseModel):
    characters: list[Character] = Field(..., min_length=1, max_length=4)


class CharacterGenResponse(BaseModel):
    character_sheet: CharacterSheet
    reference_images: dict[str, str] = Field(default_factory=dict)  # name → base64
