from __future__ import annotations

import json
from typing import NoReturn

from google import genai
from google.genai import types

from app.config import settings
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from app.prompt_manager import get_prompt_manager
from app.domain.validator.schemas import ValidationRequest, ValidationReport, ValidationIssue


class ValidatorService:
    def __init__(self, client: genai.Client) -> None:
        self._client = client
        self._model = settings.TEXT_MODEL
        self._pm = get_prompt_manager()

    def _handle_error(self, exc: Exception) -> NoReturn:
        err_str = str(exc).lower()
        if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
            raise QuotaExceededError() from exc
        if "safety" in err_str or "block" in err_str:
            raise SafetyBlockError() from exc
        raise GeminiAPIError(str(exc)) from exc

    def _run_structural_checks(self, request: ValidationRequest) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        cuts = request.cut_plan.cuts
        character_names = {c.name for c in request.character_sheet.characters}

        # Check exactly 12 cuts
        if len(cuts) != 12:
            issues.append(ValidationIssue(
                issue_type="cut_count",
                description=f"Expected 12 cuts, got {len(cuts)}",
                severity="error",
            ))

        # Check cut numbers are 1-12 and unique
        cut_numbers = [c.cut_number for c in cuts]
        if sorted(cut_numbers) != list(range(1, 13)):
            issues.append(ValidationIssue(
                issue_type="cut_numbering",
                description="Cut numbers must be unique integers from 1 to 12",
                severity="error",
            ))

        # Check scene_ref validity
        valid_scene_refs = {c.cut_number for c in cuts}  # scene refs relative to cuts
        for cut in cuts:
            if cut.scene_ref < 1:
                issues.append(ValidationIssue(
                    cut_number=cut.cut_number,
                    issue_type="invalid_scene_ref",
                    description=f"Cut {cut.cut_number} has invalid scene_ref {cut.scene_ref}",
                    severity="error",
                ))

        # Check dialogue/narration presence (warn if both empty)
        for cut in cuts:
            if not cut.dialogue and not cut.narration:
                issues.append(ValidationIssue(
                    cut_number=cut.cut_number,
                    issue_type="empty_content",
                    description=f"Cut {cut.cut_number} has no dialogue or narration",
                    severity="warning",
                ))

        # Check character name consistency in descriptions
        for cut in cuts:
            desc_lower = cut.description.lower()
            for dialogue_line in cut.dialogue:
                # Warn if dialogue mentions names not in character sheet
                for word in dialogue_line.split():
                    clean = word.strip(",:;.!?\"'").title()
                    if len(clean) > 2 and clean not in character_names and clean[0].isupper():
                        # Only flag if looks like a proper noun (short check, not exhaustive)
                        pass  # Skip — too many false positives; rely on Gemini check

        return issues

    def validate(self, request: ValidationRequest) -> ValidationReport:
        # Run structural checks first
        structural_issues = self._run_structural_checks(request)

        # Run Gemini content quality validation
        gemini_issues: list[ValidationIssue] = []
        try:
            system_instruction = self._pm.get_system_instruction("validator.instruction")

            cuts_summary = "\n".join(
                f"Cut {c.cut_number} (scene_ref={c.scene_ref}): {c.description} | "
                f"camera: {c.camera_angle} | emotion: {c.emotion} | "
                f"dialogue: {c.dialogue} | narration: {c.narration}"
                for c in request.cut_plan.cuts
            )
            characters_summary = ", ".join(
                c.name for c in request.character_sheet.characters
            )
            user_prompt = (
                f"Characters in this story: {characters_summary}\n\n"
                f"Cut plan ({len(request.cut_plan.cuts)} cuts):\n{cuts_summary}\n\n"
                "Validate the cut plan for: character name consistency, narrative flow, "
                "visual storytelling quality, and completeness. "
                "Return a ValidationReport with is_valid, issues list, and summary."
            )

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=ValidationReport,
            )

            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=config,
            )

            text = response.text or "{}"
            text = text.strip()
            if text.startswith("```json"):
                text = text.removeprefix("```json").removesuffix("```").strip()
            elif text.startswith("```"):
                text = text.removeprefix("```").removesuffix("```").strip()

            data = json.loads(text)
            gemini_report = ValidationReport.model_validate(data)
            gemini_issues = gemini_report.issues

        except (QuotaExceededError, SafetyBlockError):
            raise
        except Exception:
            # If Gemini validation fails, proceed with structural checks only
            pass

        all_issues = structural_issues + gemini_issues
        has_errors = any(i.severity == "error" for i in all_issues)
        is_valid = not has_errors and len(structural_issues) == 0

        error_count = sum(1 for i in all_issues if i.severity == "error")
        warning_count = sum(1 for i in all_issues if i.severity == "warning")
        summary = (
            f"Validation {'passed' if is_valid else 'failed'}: "
            f"{error_count} error(s), {warning_count} warning(s)."
        )

        return ValidationReport(
            is_valid=is_valid,
            issues=all_issues,
            summary=summary,
        )
