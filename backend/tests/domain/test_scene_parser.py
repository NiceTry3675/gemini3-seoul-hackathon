"""Tests for SceneParserService and its router."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.scene_parser.schemas import NovelInput, Scene, SceneBreakdown
from app.domain.scene_parser.service import SceneParserService
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from tests.conftest import mock_structured_response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(mock_client) -> SceneParserService:
    return SceneParserService(mock_client)


def _valid_scene_breakdown_json() -> str:
    return json.dumps({
        "scenes": [
            {
                "scene_number": 1,
                "title": "Opening",
                "summary": "The story begins.",
                "characters": ["Alice"],
                "mood": "tense",
                "key_dialogue": ["Hello?"],
            },
            {
                "scene_number": 2,
                "title": "Climax",
                "summary": "Conflict escalates.",
                "characters": ["Alice", "Bob"],
                "mood": "intense",
                "key_dialogue": [],
            },
        ]
    })


# ---------------------------------------------------------------------------
# Service: parse — happy path
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_prompt_manager():
    mock_pm = MagicMock()
    mock_pm.get_system_instruction.return_value = "You are a scene parser."
    with patch("app.domain.scene_parser.service.get_prompt_manager", return_value=mock_pm):
        yield mock_pm


class TestSceneParserServiceHappyPath:
    async def test_parse_returns_scene_breakdown(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(
            _valid_scene_breakdown_json()
        )
        service = _make_service(mock_genai_client)
        result = await service.parse(NovelInput(
            manuscript="Once upon a time...",
            genre="fantasy",
            tone="epic",
        ))
        assert isinstance(result, SceneBreakdown)
        assert len(result.scenes) == 2
        assert result.scenes[0].title == "Opening"

    async def test_parse_populates_scene_fields_correctly(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(
            _valid_scene_breakdown_json()
        )
        service = _make_service(mock_genai_client)
        result = await service.parse(NovelInput(manuscript="test", genre="drama", tone="dark"))
        scene = result.scenes[0]
        assert scene.scene_number == 1
        assert scene.characters == ["Alice"]
        assert scene.key_dialogue == ["Hello?"]

    async def test_parse_calls_generate_content_with_json_mime_type(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(
            _valid_scene_breakdown_json()
        )
        service = _make_service(mock_genai_client)
        await service.parse(NovelInput(manuscript="test", genre="thriller", tone="dark"))
        call_kwargs = mock_genai_client.aio.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config.response_mime_type == "application/json"

    async def test_parse_uses_system_instruction_from_prompt_manager(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(
            _valid_scene_breakdown_json()
        )
        service = _make_service(mock_genai_client)
        await service.parse(NovelInput(manuscript="test", genre="romance", tone="warm"))
        call_kwargs = mock_genai_client.aio.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        # system_instruction should be a non-empty string loaded from prompt_manager
        assert config.system_instruction is not None
        assert len(config.system_instruction) > 0


# ---------------------------------------------------------------------------
# Service: parse — manuscript boundary conditions
# ---------------------------------------------------------------------------

class TestSceneParserManuscriptBoundary:
    async def test_parse_accepts_max_length_manuscript(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(
            _valid_scene_breakdown_json()
        )
        service = _make_service(mock_genai_client)
        manuscript = "a" * 200_000
        result = await service.parse(NovelInput(manuscript=manuscript, genre="epic", tone="grand"))
        assert isinstance(result, SceneBreakdown)

    def test_novel_input_rejects_manuscript_over_max_length(self):
        with pytest.raises(Exception):
            NovelInput(manuscript="a" * 200_001, genre="epic", tone="grand")

    async def test_parse_handles_short_single_sentence_manuscript(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(
            _valid_scene_breakdown_json()
        )
        service = _make_service(mock_genai_client)
        result = await service.parse(NovelInput(manuscript="A.", genre="drama", tone="quiet"))
        assert isinstance(result, SceneBreakdown)


# ---------------------------------------------------------------------------
# Service: parse — markdown fence stripping
# ---------------------------------------------------------------------------

class TestSceneParserMarkdownFences:
    async def test_parse_strips_json_markdown_fence(self, mock_genai_client):
        fenced = f"```json\n{_valid_scene_breakdown_json()}\n```"
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(fenced)
        service = _make_service(mock_genai_client)
        result = await service.parse(NovelInput(manuscript="test", genre="sci-fi", tone="cold"))
        assert isinstance(result, SceneBreakdown)
        assert len(result.scenes) == 2

    async def test_parse_strips_plain_code_fence(self, mock_genai_client):
        fenced = f"```\n{_valid_scene_breakdown_json()}\n```"
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(fenced)
        service = _make_service(mock_genai_client)
        result = await service.parse(NovelInput(manuscript="test", genre="fantasy", tone="dark"))
        assert isinstance(result, SceneBreakdown)


# ---------------------------------------------------------------------------
# Service: parse — error handling
# ---------------------------------------------------------------------------

class TestSceneParserErrorHandling:
    async def test_parse_raises_gemini_api_error_on_invalid_json(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(
            "not valid json {{{}",
        )
        service = _make_service(mock_genai_client)
        with pytest.raises(GeminiAPIError):
            await service.parse(NovelInput(manuscript="test", genre="horror", tone="dark"))

    async def test_parse_raises_quota_exceeded_on_429(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("429 quota exceeded")
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            await service.parse(NovelInput(manuscript="test", genre="action", tone="fast"))

    async def test_parse_raises_quota_exceeded_on_resource_exhausted(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("RESOURCE_EXHAUSTED limit")
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            await service.parse(NovelInput(manuscript="test", genre="action", tone="fast"))

    async def test_parse_raises_safety_block_on_safety_error(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("safety filter triggered")
        service = _make_service(mock_genai_client)
        with pytest.raises(SafetyBlockError):
            await service.parse(NovelInput(manuscript="test", genre="horror", tone="violent"))

    async def test_parse_raises_safety_block_on_block_error(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("content blocked by policy")
        service = _make_service(mock_genai_client)
        with pytest.raises(SafetyBlockError):
            await service.parse(NovelInput(manuscript="test", genre="horror", tone="violent"))

    async def test_parse_raises_gemini_api_error_on_generic_exception(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("network timeout")
        service = _make_service(mock_genai_client)
        with pytest.raises(GeminiAPIError):
            await service.parse(NovelInput(manuscript="test", genre="drama", tone="slow"))

    async def test_parse_re_raises_quota_exceeded_without_wrapping(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = QuotaExceededError()
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            await service.parse(NovelInput(manuscript="test", genre="drama", tone="slow"))

    async def test_parse_re_raises_safety_block_without_wrapping(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = SafetyBlockError()
        service = _make_service(mock_genai_client)
        with pytest.raises(SafetyBlockError):
            await service.parse(NovelInput(manuscript="test", genre="drama", tone="slow"))

    async def test_parse_handles_response_text_none(self, mock_genai_client):
        """When response.text is None the service falls back to '{}' which fails SceneBreakdown validation."""
        response = MagicMock()
        response.text = None
        mock_genai_client.aio.models.generate_content.return_value = response
        service = _make_service(mock_genai_client)
        # '{}' is valid JSON but SceneBreakdown requires scenes list; expect GeminiAPIError or ValidationError
        with pytest.raises(Exception):
            await service.parse(NovelInput(manuscript="test", genre="drama", tone="slow"))


# ---------------------------------------------------------------------------
# Router: POST /api/pipeline/scene-parse
# ---------------------------------------------------------------------------

class TestSceneParseRouter:
    def _valid_payload(self):
        return {
            "manuscript": "Two strangers meet on a rainy night.",
            "genre": "romance",
            "tone": "warm",
            "output_language": "ko",
        }

    def test_scene_parse_returns_200_with_valid_breakdown(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(
            _valid_scene_breakdown_json()
        )
        response = test_client.post("/api/pipeline/scene-parse", json=self._valid_payload())
        assert response.status_code == 200
        data = response.json()
        assert "scenes" in data
        assert len(data["scenes"]) == 2

    def test_scene_parse_returns_422_on_missing_manuscript(self, test_client):
        response = test_client.post(
            "/api/pipeline/scene-parse",
            json={"genre": "romance", "tone": "warm"},
        )
        assert response.status_code == 422

    def test_scene_parse_uses_default_genre_when_missing(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(
            _valid_scene_breakdown_json()
        )
        response = test_client.post(
            "/api/pipeline/scene-parse",
            json={"manuscript": "test", "tone": "warm"},
        )
        assert response.status_code == 200

    def test_scene_parse_returns_429_on_quota_exceeded(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("429 quota exceeded")
        response = test_client.post("/api/pipeline/scene-parse", json=self._valid_payload())
        assert response.status_code == 429

    def test_scene_parse_returns_422_on_safety_block(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("safety block triggered")
        response = test_client.post("/api/pipeline/scene-parse", json=self._valid_payload())
        assert response.status_code == 422

    def test_scene_parse_returns_502_on_gemini_api_error(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("network timeout")
        response = test_client.post("/api/pipeline/scene-parse", json=self._valid_payload())
        assert response.status_code == 502

    def test_scene_parse_uses_default_output_language(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = mock_structured_response(
            _valid_scene_breakdown_json()
        )
        payload = {"manuscript": "test", "genre": "drama", "tone": "dark"}
        response = test_client.post("/api/pipeline/scene-parse", json=payload)
        assert response.status_code == 200
