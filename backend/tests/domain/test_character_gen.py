"""Tests for CharacterGenService and its router."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, call

import pytest

from app.domain.character_gen.schemas import (
    Character,
    CharacterGenRequest,
    CharacterGenResponse,
    CharacterSheet,
)
from app.domain.character_gen.service import CharacterGenService
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from tests.conftest import mock_structured_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(mock_client) -> CharacterGenService:
    return CharacterGenService(mock_client)


def _character_sheet_json(names: list[str] | None = None) -> str:
    if names is None:
        names = ["Alice", "Bob"]
    characters = [
        {
            "name": n,
            "appearance": f"{n} looks distinctive",
            "personality": "complex",
            "role": "main",
            "visual_prompt": f"portrait of {n}, realistic",
        }
        for n in names
    ]
    return json.dumps({"characters": characters})


def _make_image_response(data: bytes = b"fake-image-bytes") -> MagicMock:
    """Build a mock response with inline_data for image generation."""
    part = MagicMock()
    part.inline_data = MagicMock()
    part.inline_data.data = data
    content = MagicMock()
    content.parts = [part]
    candidate = MagicMock()
    candidate.content = content
    response = MagicMock()
    response.candidates = [candidate]
    return response


# ---------------------------------------------------------------------------
# Service: generate — happy path
# ---------------------------------------------------------------------------

class TestCharacterGenServiceHappyPath:
    def test_generate_returns_character_gen_response(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        # First call: character sheet; subsequent calls: reference images
        sheet_resp = mock_structured_response(_character_sheet_json())
        img_resp = _make_image_response()
        mock_genai_client.models.generate_content.side_effect = [sheet_resp, img_resp, img_resp]

        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        result = service.generate(req)

        assert isinstance(result, CharacterGenResponse)
        assert isinstance(result.character_sheet, CharacterSheet)

    def test_generate_includes_reference_images_for_each_character(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        sheet_resp = mock_structured_response(_character_sheet_json(["Alice", "Bob"]))
        img_resp = _make_image_response()
        mock_genai_client.models.generate_content.side_effect = [sheet_resp, img_resp, img_resp]

        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        result = service.generate(req)

        assert "Alice" in result.reference_images
        assert "Bob" in result.reference_images

    def test_generate_single_character_has_one_reference_image(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        sheet_resp = mock_structured_response(_character_sheet_json(["Alice"]))
        img_resp = _make_image_response()
        mock_genai_client.models.generate_content.side_effect = [sheet_resp, img_resp]

        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        result = service.generate(req)

        assert len(result.reference_images) == 1
        assert "Alice" in result.reference_images

    def test_generate_four_characters_all_images_succeed(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        names = ["Alice", "Bob", "Carol", "Dave"]
        sheet_resp = mock_structured_response(_character_sheet_json(names))
        img_resp = _make_image_response()
        mock_genai_client.models.generate_content.side_effect = (
            [sheet_resp] + [img_resp] * 4
        )

        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        result = service.generate(req)

        assert len(result.reference_images) == 4
        for name in names:
            assert name in result.reference_images

    def test_generate_reference_images_contain_base64_strings(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        import base64
        raw = b"image-data"
        expected_b64 = base64.b64encode(raw).decode()

        sheet_resp = mock_structured_response(_character_sheet_json(["Alice"]))
        img_resp = _make_image_response(data=raw)
        mock_genai_client.models.generate_content.side_effect = [sheet_resp, img_resp]

        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        result = service.generate(req)

        assert result.reference_images["Alice"] == expected_b64


# ---------------------------------------------------------------------------
# Service: generate — reference image failures are silently swallowed
# ---------------------------------------------------------------------------

class TestCharacterGenImageFailures:
    def test_reference_image_failure_results_in_empty_dict(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        sheet_resp = mock_structured_response(_character_sheet_json(["Alice"]))
        mock_genai_client.models.generate_content.side_effect = [
            sheet_resp,
            Exception("image generation failed"),
        ]

        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        result = service.generate(req)

        assert result.reference_images == {}
        assert isinstance(result.character_sheet, CharacterSheet)

    def test_all_reference_images_fail_returns_empty_reference_images(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        sheet_resp = mock_structured_response(_character_sheet_json(["Alice", "Bob"]))
        mock_genai_client.models.generate_content.side_effect = [
            sheet_resp,
            Exception("fail alice"),
            Exception("fail bob"),
        ]

        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        result = service.generate(req)

        assert result.reference_images == {}

    def test_partial_image_failures_only_include_successful_images(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        sheet_resp = mock_structured_response(_character_sheet_json(["Alice", "Bob"]))
        img_resp = _make_image_response()
        mock_genai_client.models.generate_content.side_effect = [
            sheet_resp,
            img_resp,                        # Alice succeeds
            Exception("bob image failed"),   # Bob fails
        ]

        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        result = service.generate(req)

        assert "Alice" in result.reference_images
        assert "Bob" not in result.reference_images

    def test_image_response_with_no_inline_data_returns_none_image(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        """A candidate part with inline_data=None causes _generate_reference_image to return None."""
        sheet_resp = mock_structured_response(_character_sheet_json(["Alice"]))

        part = MagicMock()
        part.inline_data = None
        content = MagicMock()
        content.parts = [part]
        candidate = MagicMock()
        candidate.content = content
        img_resp = MagicMock()
        img_resp.candidates = [candidate]

        mock_genai_client.models.generate_content.side_effect = [sheet_resp, img_resp]

        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        result = service.generate(req)

        assert result.reference_images == {}

    def test_quota_error_in_image_gen_is_silently_caught(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        """QuotaExceededError in image gen should be caught silently (not propagate)."""
        sheet_resp = mock_structured_response(_character_sheet_json(["Alice"]))
        mock_genai_client.models.generate_content.side_effect = [
            sheet_resp,
            QuotaExceededError(),
        ]

        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        result = service.generate(req)

        assert result.reference_images == {}


# ---------------------------------------------------------------------------
# Service: generate — character sheet errors propagate
# ---------------------------------------------------------------------------

class TestCharacterGenSheetErrors:
    def test_invalid_json_in_sheet_response_raises_gemini_api_error(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        mock_genai_client.models.generate_content.return_value = mock_structured_response(
            "not json {{{"
        )
        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        with pytest.raises(GeminiAPIError):
            service.generate(req)

    def test_quota_exceeded_in_sheet_gen_propagates(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("429 quota exceeded")
        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        with pytest.raises(QuotaExceededError):
            service.generate(req)

    def test_safety_block_in_sheet_gen_propagates(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("safety block triggered")
        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        with pytest.raises(SafetyBlockError):
            service.generate(req)

    def test_generic_exception_in_sheet_gen_raises_gemini_api_error(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("connection error")
        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        with pytest.raises(GeminiAPIError):
            service.generate(req)

    def test_markdown_fenced_sheet_response_is_parsed(
        self, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        fenced = f"```json\n{_character_sheet_json(['Alice'])}\n```"
        img_resp = _make_image_response()
        mock_genai_client.models.generate_content.side_effect = [
            mock_structured_response(fenced),
            img_resp,
        ]
        service = _make_service(mock_genai_client)
        req = CharacterGenRequest(
            novel_input=sample_novel_input,
            scene_breakdown=sample_scene_breakdown,
        )
        result = service.generate(req)
        assert result.character_sheet.characters[0].name == "Alice"


# ---------------------------------------------------------------------------
# Router: POST /api/pipeline/character-gen
# ---------------------------------------------------------------------------

class TestCharacterGenRouter:
    def _valid_payload(self, sample_novel_input, sample_scene_breakdown):
        return {
            "novel_input": sample_novel_input.model_dump(),
            "scene_breakdown": sample_scene_breakdown.model_dump(),
        }

    def test_character_gen_returns_200(
        self, test_client, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        sheet_resp = mock_structured_response(_character_sheet_json(["Alice"]))
        img_resp = _make_image_response()
        mock_genai_client.models.generate_content.side_effect = [sheet_resp, img_resp]

        response = test_client.post(
            "/api/pipeline/character-gen",
            json=self._valid_payload(sample_novel_input, sample_scene_breakdown),
        )
        assert response.status_code == 200
        data = response.json()
        assert "character_sheet" in data
        assert "reference_images" in data

    def test_character_gen_returns_422_on_missing_fields(self, test_client):
        response = test_client.post("/api/pipeline/character-gen", json={})
        assert response.status_code == 422

    def test_character_gen_returns_429_on_quota_exceeded(
        self, test_client, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("429 quota exceeded")
        response = test_client.post(
            "/api/pipeline/character-gen",
            json=self._valid_payload(sample_novel_input, sample_scene_breakdown),
        )
        assert response.status_code == 429

    def test_character_gen_returns_422_on_safety_block(
        self, test_client, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("safety block triggered")
        response = test_client.post(
            "/api/pipeline/character-gen",
            json=self._valid_payload(sample_novel_input, sample_scene_breakdown),
        )
        assert response.status_code == 422

    def test_character_gen_returns_502_on_api_error(
        self, test_client, mock_genai_client, sample_novel_input, sample_scene_breakdown
    ):
        mock_genai_client.models.generate_content.side_effect = Exception("network error")
        response = test_client.post(
            "/api/pipeline/character-gen",
            json=self._valid_payload(sample_novel_input, sample_scene_breakdown),
        )
        assert response.status_code == 502
