from pydantic import BaseModel, Field
from enum import Enum


class Genre(str, Enum):
    MYSTERY = "mystery"
    SF = "sf"
    ROMANCE = "romance"
    FANTASY = "fantasy"
    SLICE_OF_LIFE = "slice_of_life"


class Tone(str, Enum):
    DARK = "dark"
    COMIC = "comic"
    EMOTIONAL = "emotional"
    EERIE = "eerie"


class Rating(str, Enum):
    ALL = "all"
    AGE_12 = "12"
    AGE_15 = "15"


class NovelInput(BaseModel):
    manuscript: str = Field(..., max_length=2000)
    genre: Genre
    tone: Tone
    rating: Rating = Rating.ALL
    output_language: str = Field("ko", description="ko|en|ja|zh")


class Scene(BaseModel):
    scene_id: str
    summary: str
    emotion: str
    key_action: str
    background: str
    characters_present: list[str]


class SceneBreakdown(BaseModel):
    scenes: list[Scene] = Field(..., min_length=2, max_length=6)


class Character(BaseModel):
    name: str
    name_en: str
    appearance_keywords: list[str] = Field(..., min_length=5, max_length=5)
    personality_one_word: str
    prohibited_visuals: list[str]


class CharacterSheet(BaseModel):
    characters: list[Character] = Field(..., min_length=1, max_length=4)


class Cut(BaseModel):
    id: int = Field(..., ge=1, le=12)
    scene_ref: str
    action: str
    dialogue: str = Field("", max_length=35)
    narration: str = Field("")
    sfx: str = Field("")
    camera: str
    mood: str
    characters_in_frame: list[str]
    background: str


class CutPlan(BaseModel):
    cuts: list[Cut] = Field(..., min_length=12, max_length=12)


class ValidationResult(BaseModel):
    cut_id: int
    is_valid: bool
    issues: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    results: list[ValidationResult]
    all_passed: bool


class GeneratedCut(BaseModel):
    cut_id: int
    image_base64: str
    prompt_used: str


class ContiResult(BaseModel):
    characters: CharacterSheet
    cuts: CutPlan
    images: list[GeneratedCut]
