from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.cut_planner.schemas import CutPlan
from app.domain.character_gen.schemas import CharacterSheet


class ValidationRequest(BaseModel):
    cut_plan: CutPlan
    character_sheet: CharacterSheet


class ValidationIssue(BaseModel):
    cut_number: int | None = None
    issue_type: str
    description: str
    severity: str = Field(..., pattern="^(error|warning)$")


class ValidationReport(BaseModel):
    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    summary: str
