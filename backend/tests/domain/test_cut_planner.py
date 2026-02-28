"""Tests for CutPlannerService and its router."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.domain.cut_planner.schemas import CutPlan, CutPlanRequest
from app.domain.cut_planner.service import CutPlannerService
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from tests.conftest import mock_structured_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(mock_client) -> CutPlannerService:
    return CutPlannerService(mock_client)


def _valid_cut_plan_json() -> str:
    cuts = [
        {
            "cut_number": i,
            "scene_ref": 1 if i <= 6 else 2,
            "description": f"Description of cut {i}",
            "dialogue": [f"Dialogue {i}"],
            "narration": f"Narration {i}",
            "camera_angle": "wide shot",
            "emotion": "neutral",
            "image_prompt": f"image prompt for cut {i}",
        }
        for i in range(1, 13)
    ]
    return json.dumps({"cuts": cuts})


# ---------------------------------------------------------------------------
# Service: plan — happy path
# ---------------------------------------------------------------------------

class TestCutPlannerServiceHappyPath:
    def test_plan_returns_cut_plan(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_cut_plan_json()
        )
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        result = service.plan(req)
        assert isinstance(result, CutPlan)

    def test_plan_returns_exactly_12_cuts(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_cut_plan_json()
        )
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        result = service.plan(req)
        assert len(result.cuts) == 12

    def test_plan_cut_numbers_are_1_through_12(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_cut_plan_json()
        )
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        result = service.plan(req)
        cut_numbers = sorted(c.cut_number for c in result.cuts)
        assert cut_numbers == list(range(1, 13))

    def test_plan_calls_generate_content_with_json_mime_type(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_cut_plan_json()
        )
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        service.plan(req)
        call_kwargs = mock_genai_client.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.response_mime_type == "application/json"


# ---------------------------------------------------------------------------
# Service: plan — markdown fence stripping
# ---------------------------------------------------------------------------

class TestCutPlannerMarkdownFences:
    def test_plan_strips_json_markdown_fence(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        fenced = f"```json\n{_valid_cut_plan_json()}\n```"
        mock_genai_client.models.generate_content.return_value = mock_structured_response(fenced)
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        result = service.plan(req)
        assert len(result.cuts) == 12

    def test_plan_strips_plain_code_fence(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        fenced = f"```\n{_valid_cut_plan_json()}\n```"
        mock_genai_client.models.generate_content.return_value = mock_structured_response(fenced)
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        result = service.plan(req)
        assert len(result.cuts) == 12


# ---------------------------------------------------------------------------
# Service: plan — error handling
# ---------------------------------------------------------------------------

class TestCutPlannerErrorHandling:
    def test_plan_raises_gemini_api_error_on_invalid_json(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            "not valid json {{{"
        )
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        with pytest.raises(GeminiAPIError):
            service.plan(req)

    def test_plan_raises_quota_exceeded_on_429(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("429 quota exceeded")
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        with pytest.raises(QuotaExceededError):
            service.plan(req)

    def test_plan_raises_quota_exceeded_on_resource_exhausted(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("RESOURCE_EXHAUSTED")
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        with pytest.raises(QuotaExceededError):
            service.plan(req)

    def test_plan_raises_safety_block_on_safety_error(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("safety block triggered")
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        with pytest.raises(SafetyBlockError):
            service.plan(req)

    def test_plan_raises_gemini_api_error_on_generic_exception(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("network timeout")
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        with pytest.raises(GeminiAPIError):
            service.plan(req)

    def test_plan_re_raises_quota_exceeded_without_wrapping(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = QuotaExceededError()
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        with pytest.raises(QuotaExceededError):
            service.plan(req)

    def test_plan_re_raises_safety_block_without_wrapping(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = SafetyBlockError()
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        with pytest.raises(SafetyBlockError):
            service.plan(req)

    def test_plan_handles_response_text_none(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        """None text falls back to '{}', which fails CutPlan validation -> GeminiAPIError or similar."""
        response = MagicMock()
        response.text = None
        mock_genai_client.models.generate_content.return_value = response
        service = _make_service(mock_genai_client)
        req = CutPlanRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
            character_sheet=sample_character_sheet,
        )
        with pytest.raises(Exception):
            service.plan(req)


# ---------------------------------------------------------------------------
# Router: POST /api/pipeline/cut-plan
# ---------------------------------------------------------------------------

class TestCutPlannerRouter:
    def _valid_payload(self, sample_novel_input, sample_scene_breakdown, sample_character_sheet):
        return {
            "novel_input": sample_novel_input.model_dump(),
            "scene_breakdown": sample_scene_breakdown.model_dump(),
            "character_sheet": sample_character_sheet.model_dump(),
        }

    def test_cut_plan_returns_200_with_valid_plan(
        self, test_client, mock_genai_client,
        sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            _valid_cut_plan_json()
        )
        response = test_client.post(
            "/api/pipeline/cut-plan",
            json=self._valid_payload(sample_novel_input, sample_scene_breakdown, sample_character_sheet),
        )
        assert response.status_code == 200
        data = response.json()
        assert "cuts" in data
        assert len(data["cuts"]) == 12

    def test_cut_plan_returns_422_on_missing_fields(self, test_client):
        response = test_client.post("/api/pipeline/cut-plan", json={})
        assert response.status_code == 422

    def test_cut_plan_returns_429_on_quota_exceeded(
        self, test_client, mock_genai_client,
        sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("429 quota exceeded")
        response = test_client.post(
            "/api/pipeline/cut-plan",
            json=self._valid_payload(sample_novel_input, sample_scene_breakdown, sample_character_sheet),
        )
        assert response.status_code == 429

    def test_cut_plan_returns_422_on_safety_block(
        self, test_client, mock_genai_client,
        sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("safety block triggered")
        response = test_client.post(
            "/api/pipeline/cut-plan",
            json=self._valid_payload(sample_novel_input, sample_scene_breakdown, sample_character_sheet),
        )
        assert response.status_code == 422

    def test_cut_plan_returns_502_on_api_error(
        self, test_client, mock_genai_client,
        sample_novel_input, sample_scene_breakdown, sample_character_sheet
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("network timeout")
        response = test_client.post(
            "/api/pipeline/cut-plan",
            json=self._valid_payload(sample_novel_input, sample_scene_breakdown, sample_character_sheet),
        )
        assert response.status_code == 502
