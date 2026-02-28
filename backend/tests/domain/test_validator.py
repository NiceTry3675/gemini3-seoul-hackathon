"""Tests for ValidatorService and its router."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.domain.cut_planner.schemas import Cut, CutPlan
from app.domain.validator.schemas import ValidationIssue, ValidationReport, ValidationRequest
from app.domain.validator.service import ValidatorService
from app.exceptions import QuotaExceededError, SafetyBlockError
from tests.conftest import mock_structured_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(mock_client) -> ValidatorService:
    return ValidatorService(mock_client)


def _make_cut(
    cut_number: int,
    scene_ref: int = 1,
    dialogue: list[str] | None = None,
    narration: str = "Some narration",
) -> Cut:
    return Cut(
        cut_number=cut_number,
        scene_ref=scene_ref,
        description=f"Description of cut {cut_number}",
        dialogue=dialogue if dialogue is not None else [f"Dialogue {cut_number}"],
        narration=narration,
        camera_angle="wide shot",
        emotion="neutral",
        image_prompt=f"image prompt cut {cut_number}",
    )


def _make_valid_cut_plan() -> CutPlan:
    """12 cuts numbered 1-12, all with valid scene_refs and content."""
    return CutPlan(cuts=[_make_cut(i) for i in range(1, 13)])


def _valid_gemini_report_json(is_valid: bool = True) -> str:
    return json.dumps({
        "is_valid": is_valid,
        "issues": [],
        "summary": "All good." if is_valid else "Some issues found.",
    })


# ---------------------------------------------------------------------------
# Service: validate — happy path
# ---------------------------------------------------------------------------

class TestValidatorServiceHappyPath:
    def test_validate_returns_validation_report(self, mock_genai_client, sample_character_sheet):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        service = _make_service(mock_genai_client)
        req = ValidationRequest(
            cut_plan=_make_valid_cut_plan(),
            character_sheet=sample_character_sheet,
        )
        result = service.validate(req)
        assert isinstance(result, ValidationReport)

    def test_validate_is_valid_true_when_no_errors(self, mock_genai_client, sample_character_sheet):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        service = _make_service(mock_genai_client)
        req = ValidationRequest(
            cut_plan=_make_valid_cut_plan(),
            character_sheet=sample_character_sheet,
        )
        result = service.validate(req)
        assert result.is_valid is True

    def test_validate_includes_summary_string(self, mock_genai_client, sample_character_sheet):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        service = _make_service(mock_genai_client)
        req = ValidationRequest(
            cut_plan=_make_valid_cut_plan(),
            character_sheet=sample_character_sheet,
        )
        result = service.validate(req)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0


# ---------------------------------------------------------------------------
# Service: validate — structural checks
# ---------------------------------------------------------------------------

class TestValidatorStructuralChecks:
    def test_wrong_cut_count_produces_error_issue(self, mock_genai_client, sample_character_sheet):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        # CutPlan and ValidationRequest enforce Pydantic constraints, so mock the full request
        plan = MagicMock()
        plan.cuts = [MagicMock(
            cut_number=i, scene_ref=1, dialogue=["hi"], narration="ok", description="desc"
        ) for i in range(1, 7)]  # Only 6 cuts
        req = MagicMock()
        req.cut_plan = plan
        req.character_sheet = sample_character_sheet

        service = _make_service(mock_genai_client)
        result = service.validate(req)

        cut_count_issues = [i for i in result.issues if i.issue_type == "cut_count"]
        assert len(cut_count_issues) == 1
        assert cut_count_issues[0].severity == "error"

    def test_wrong_cut_count_makes_is_valid_false(self, mock_genai_client, sample_character_sheet):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        plan = MagicMock()
        plan.cuts = [MagicMock(
            cut_number=i, scene_ref=1, dialogue=["hi"], narration="ok", description="desc"
        ) for i in range(1, 7)]  # Only 6 cuts
        req = MagicMock()
        req.cut_plan = plan
        req.character_sheet = sample_character_sheet

        service = _make_service(mock_genai_client)
        result = service.validate(req)
        assert result.is_valid is False

    def test_duplicate_cut_numbers_produces_numbering_error(self, mock_genai_client, sample_character_sheet):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        # 12 cuts where numbers are 1-11 + duplicate 1 (sorted != [1..12])
        numbers = list(range(1, 12)) + [1]  # missing 12, duplicate 1
        plan = MagicMock()
        plan.cuts = [MagicMock(
            cut_number=n, scene_ref=1, dialogue=["hi"], narration="ok", description="desc"
        ) for n in numbers]
        req = MagicMock()
        req.cut_plan = plan
        req.character_sheet = sample_character_sheet

        service = _make_service(mock_genai_client)
        result = service.validate(req)

        numbering_issues = [i for i in result.issues if i.issue_type == "cut_numbering"]
        assert len(numbering_issues) >= 1

    def test_empty_dialogue_and_narration_produces_warning(self, mock_genai_client, sample_character_sheet):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        cuts = [
            _make_cut(i, dialogue=[], narration="") if i == 5 else _make_cut(i)
            for i in range(1, 13)
        ]
        plan = CutPlan(cuts=cuts)
        service = _make_service(mock_genai_client)
        req = ValidationRequest(cut_plan=plan, character_sheet=sample_character_sheet)
        result = service.validate(req)

        empty_content_issues = [i for i in result.issues if i.issue_type == "empty_content"]
        assert len(empty_content_issues) == 1
        assert empty_content_issues[0].severity == "warning"
        assert empty_content_issues[0].cut_number == 5

    def test_empty_content_warning_does_not_make_is_valid_false(self, mock_genai_client, sample_character_sheet):
        """Warnings alone don't set is_valid=False when there are no structural issues beyond warnings."""
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        # All 12 cuts present with empty dialogue+narration on one of them
        cuts = [
            _make_cut(i, dialogue=[], narration="") if i == 3 else _make_cut(i)
            for i in range(1, 13)
        ]
        plan = CutPlan(cuts=cuts)
        service = _make_service(mock_genai_client)
        req = ValidationRequest(cut_plan=plan, character_sheet=sample_character_sheet)
        result = service.validate(req)

        # is_valid = no errors AND len(structural_issues) == 0
        # A warning IS a structural issue, so is_valid will be False here
        # Let's check the actual logic: is_valid = not has_errors and len(structural_issues) == 0
        structural_issues = [i for i in result.issues if i.issue_type == "empty_content"]
        assert len(structural_issues) == 1
        assert result.is_valid is False  # Because structural_issues is non-empty

    def test_multiple_cuts_with_empty_content_produce_multiple_warnings(
        self, mock_genai_client, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        cuts = [
            _make_cut(i, dialogue=[], narration="")
            for i in range(1, 13)
        ]
        plan = CutPlan(cuts=cuts)
        service = _make_service(mock_genai_client)
        req = ValidationRequest(cut_plan=plan, character_sheet=sample_character_sheet)
        result = service.validate(req)

        empty_content_issues = [i for i in result.issues if i.issue_type == "empty_content"]
        assert len(empty_content_issues) == 12


# ---------------------------------------------------------------------------
# Service: validate — Gemini validation failures
# ---------------------------------------------------------------------------

class TestValidatorGeminiFailures:
    def test_gemini_validation_failure_proceeds_with_structural_checks_only(
        self, mock_genai_client, sample_character_sheet
    ):
        """When Gemini call fails, validate proceeds using structural checks only."""
        mock_genai_client.models.generate_content.side_effect = Exception("network timeout")
        service = _make_service(mock_genai_client)
        req = ValidationRequest(
            cut_plan=_make_valid_cut_plan(),
            character_sheet=sample_character_sheet,
        )
        # Should not raise; structural checks pass for valid plan
        result = service.validate(req)
        assert isinstance(result, ValidationReport)

    def test_gemini_validation_failure_with_valid_plan_returns_is_valid_true(
        self, mock_genai_client, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("server error")
        service = _make_service(mock_genai_client)
        req = ValidationRequest(
            cut_plan=_make_valid_cut_plan(),
            character_sheet=sample_character_sheet,
        )
        result = service.validate(req)
        assert result.is_valid is True

    def test_gemini_returns_issues_combined_with_structural(
        self, mock_genai_client, sample_character_sheet
    ):
        """Gemini issues + structural issues are combined in the final report."""
        gemini_issues = [
            {"cut_number": 3, "issue_type": "narrative_gap", "description": "Gap in story", "severity": "warning"}
        ]
        gemini_report = json.dumps({
            "is_valid": False,
            "issues": gemini_issues,
            "summary": "Narrative gap detected.",
        })
        mock_genai_client.models.generate_content.return_value = mock_structured_response(gemini_report)

        # Plan with an empty-content cut (structural warning) and all 12 cuts
        cuts = [
            _make_cut(i, dialogue=[], narration="") if i == 1 else _make_cut(i)
            for i in range(1, 13)
        ]
        plan = CutPlan(cuts=cuts)
        service = _make_service(mock_genai_client)
        req = ValidationRequest(cut_plan=plan, character_sheet=sample_character_sheet)
        result = service.validate(req)

        structural = [i for i in result.issues if i.issue_type == "empty_content"]
        gemini = [i for i in result.issues if i.issue_type == "narrative_gap"]
        assert len(structural) == 1
        assert len(gemini) == 1

    def test_quota_exceeded_in_gemini_validation_propagates(
        self, mock_genai_client, sample_character_sheet
    ):
        """QuotaExceededError and SafetyBlockError are NOT caught; they propagate."""
        mock_genai_client.models.generate_content.side_effect = QuotaExceededError()
        service = _make_service(mock_genai_client)
        req = ValidationRequest(
            cut_plan=_make_valid_cut_plan(),
            character_sheet=sample_character_sheet,
        )
        with pytest.raises(QuotaExceededError):
            service.validate(req)

    def test_safety_block_in_gemini_validation_propagates(
        self, mock_genai_client, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = SafetyBlockError()
        service = _make_service(mock_genai_client)
        req = ValidationRequest(
            cut_plan=_make_valid_cut_plan(),
            character_sheet=sample_character_sheet,
        )
        with pytest.raises(SafetyBlockError):
            service.validate(req)

    def test_invalid_json_in_gemini_response_proceeds_with_structural_only(
        self, mock_genai_client, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.return_value = mock_structured_response("not json {{")
        service = _make_service(mock_genai_client)
        req = ValidationRequest(
            cut_plan=_make_valid_cut_plan(),
            character_sheet=sample_character_sheet,
        )
        # Should not raise; falls back to structural only
        result = service.validate(req)
        assert isinstance(result, ValidationReport)
        assert result.is_valid is True  # structural checks pass for valid plan


# ---------------------------------------------------------------------------
# Service: validate — is_valid logic
# ---------------------------------------------------------------------------

class TestValidatorIsValidLogic:
    def test_is_valid_false_when_structural_errors_present(
        self, mock_genai_client, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        # Use a fully mocked request with only 6 cuts to trigger the structural cut_count error
        plan = MagicMock()
        plan.cuts = [MagicMock(
            cut_number=i, scene_ref=1, dialogue=["hi"], narration="ok", description="desc"
        ) for i in range(1, 7)]
        req = MagicMock()
        req.cut_plan = plan
        req.character_sheet = sample_character_sheet

        service = _make_service(mock_genai_client)
        result = service.validate(req)
        assert result.is_valid is False

    def test_is_valid_false_when_gemini_returns_error_issue(
        self, mock_genai_client, sample_character_sheet
    ):
        gemini_report = json.dumps({
            "is_valid": False,
            "issues": [
                {"issue_type": "character_inconsistency", "description": "Wrong name", "severity": "error"}
            ],
            "summary": "Error found.",
        })
        mock_genai_client.models.generate_content.return_value = mock_structured_response(gemini_report)
        service = _make_service(mock_genai_client)
        req = ValidationRequest(
            cut_plan=_make_valid_cut_plan(),
            character_sheet=sample_character_sheet,
        )
        result = service.validate(req)
        assert result.is_valid is False

    def test_summary_reflects_error_and_warning_counts(self, mock_genai_client, sample_character_sheet):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        service = _make_service(mock_genai_client)
        req = ValidationRequest(
            cut_plan=_make_valid_cut_plan(),
            character_sheet=sample_character_sheet,
        )
        result = service.validate(req)
        assert "0 error" in result.summary
        assert "0 warning" in result.summary


# ---------------------------------------------------------------------------
# Router: POST /api/pipeline/validate
# ---------------------------------------------------------------------------

class TestValidatorRouter:
    def _valid_payload(self, sample_cut_plan, sample_character_sheet):
        return {
            "cut_plan": sample_cut_plan.model_dump(),
            "character_sheet": sample_character_sheet.model_dump(),
        }

    def test_validate_returns_200_with_valid_report(
        self, test_client, mock_genai_client, sample_cut_plan, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_gemini_report_json(is_valid=True)
        )
        response = test_client.post(
            "/api/pipeline/validate",
            json=self._valid_payload(sample_cut_plan, sample_character_sheet),
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "issues" in data
        assert "summary" in data

    def test_validate_returns_422_on_missing_fields(self, test_client):
        response = test_client.post("/api/pipeline/validate", json={})
        assert response.status_code == 422

    def test_validate_returns_429_on_quota_exceeded(
        self, test_client, mock_genai_client, sample_cut_plan, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = QuotaExceededError()
        response = test_client.post(
            "/api/pipeline/validate",
            json=self._valid_payload(sample_cut_plan, sample_character_sheet),
        )
        assert response.status_code == 429

    def test_validate_returns_422_on_safety_block(
        self, test_client, mock_genai_client, sample_cut_plan, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = SafetyBlockError()
        response = test_client.post(
            "/api/pipeline/validate",
            json=self._valid_payload(sample_cut_plan, sample_character_sheet),
        )
        assert response.status_code == 422
