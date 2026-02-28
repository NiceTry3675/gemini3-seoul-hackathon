from __future__ import annotations

from pydantic import BaseModel, Field


class NovelInput(BaseModel):
    manuscript: str = Field(..., max_length=200_000)
    genre: str = ""
    tone: str = ""
    output_language: str = Field(default="ko")


class Scene(BaseModel):
    scene_number: int = Field(..., ge=1)
    title: str
    summary: str
    characters: list[str]
    mood: str
    key_dialogue: list[str] = Field(default_factory=list)


class SceneBreakdown(BaseModel):
    scenes: list[Scene] = Field(..., min_length=2, max_length=6)
