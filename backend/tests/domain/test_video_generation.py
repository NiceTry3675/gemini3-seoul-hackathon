"""Tests for video generation service and router."""
from __future__ import annotations

import base64
from unittest.mock import MagicMock, PropertyMock

import pytest

from app.domain.video_generation.schemas import VideoGenerationRequest
from app.domain.video_generation.service import GeminiVideoService
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(mock_client) -> GeminiVideoService:
    return GeminiVideoService(mock_client)


def _make_completed_operation(video_bytes: bytes = b"fake-video-data") -> MagicMock:
    """Create a mock operation that is already done with video data."""
    video = MagicMock()
    video.video.video_bytes = video_bytes

    operation = MagicMock()
    operation.done = True
    operation.response.generated_videos = [video]
    return operation


def _make_polling_operation(video_bytes: bytes = b"fake-video-data") -> tuple[MagicMock, MagicMock]:
    """Create a mock operation that requires one polling round.

    Returns (initial_operation, completed_operation).
    """
    completed = _make_completed_operation(video_bytes)

    initial = MagicMock()
    initial.done = False

    return initial, completed


# ---------------------------------------------------------------------------
# Service: generate
# ---------------------------------------------------------------------------

class TestGeminiVideoServiceGenerate:
    def test_generate_returns_video_base64(self, mock_genai_client):
        video_bytes = b"test-video-content"
        operation = _make_completed_operation(video_bytes)
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        request = VideoGenerationRequest(prompt="A sunset over the ocean")
        result = service.generate(request)

        expected_b64 = base64.b64encode(video_bytes).decode("utf-8")
        assert result.video_base64 == expected_b64
        assert result.mime_type == "video/mp4"

    def test_generate_polls_until_done(self, mock_genai_client):
        video_bytes = b"polled-video"
        initial, completed = _make_polling_operation(video_bytes)
        mock_genai_client.models.generate_videos.return_value = initial
        mock_genai_client.operations.get.return_value = completed

        service = _make_service(mock_genai_client)
        request = VideoGenerationRequest(prompt="A cat playing")
        result = service.generate(request)

        mock_genai_client.operations.get.assert_called_once_with(initial)
        expected_b64 = base64.b64encode(video_bytes).decode("utf-8")
        assert result.video_base64 == expected_b64

    def test_generate_passes_aspect_ratio(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        request = VideoGenerationRequest(prompt="test", aspect_ratio="9:16")
        service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        config = call_kwargs.kwargs.get("config")
        assert config.aspect_ratio == "9:16"

    def test_generate_passes_negative_prompt(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        request = VideoGenerationRequest(prompt="test", negative_prompt="blurry")
        service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        config = call_kwargs.kwargs.get("config")
        assert config.negative_prompt == "blurry"

    def test_generate_raises_quota_exceeded_on_429(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = Exception("429 quota exceeded")
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            service.generate(VideoGenerationRequest(prompt="test"))

    def test_generate_raises_quota_exceeded_on_resource_exhausted(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = Exception("RESOURCE_EXHAUSTED")
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            service.generate(VideoGenerationRequest(prompt="test"))

    def test_generate_raises_safety_block(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = Exception("safety block triggered")
        service = _make_service(mock_genai_client)
        with pytest.raises(SafetyBlockError):
            service.generate(VideoGenerationRequest(prompt="test"))

    def test_generate_raises_gemini_api_error_on_generic_exception(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = Exception("network timeout")
        service = _make_service(mock_genai_client)
        with pytest.raises(GeminiAPIError):
            service.generate(VideoGenerationRequest(prompt="test"))

    def test_generate_re_raises_quota_exceeded_without_wrapping(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = QuotaExceededError()
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            service.generate(VideoGenerationRequest(prompt="test"))

    def test_generate_re_raises_safety_block_without_wrapping(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = SafetyBlockError()
        service = _make_service(mock_genai_client)
        with pytest.raises(SafetyBlockError):
            service.generate(VideoGenerationRequest(prompt="test"))


# ---------------------------------------------------------------------------
# Router: POST /api/video/generate
# ---------------------------------------------------------------------------

class TestVideoGenerationRouter:
    def test_generate_returns_200(self, test_client, mock_genai_client):
        operation = _make_completed_operation(b"router-video")
        mock_genai_client.models.generate_videos.return_value = operation

        response = test_client.post(
            "/api/video/generate",
            json={"prompt": "A beautiful sunset"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["video_base64"] == base64.b64encode(b"router-video").decode("utf-8")
        assert data["mime_type"] == "video/mp4"

    def test_generate_with_aspect_ratio(self, test_client, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        response = test_client.post(
            "/api/video/generate",
            json={"prompt": "test", "aspect_ratio": "9:16"},
        )
        assert response.status_code == 200

    def test_generate_missing_prompt_returns_422(self, test_client):
        response = test_client.post("/api/video/generate", json={})
        assert response.status_code == 422

    def test_generate_quota_exceeded_returns_429(self, test_client, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = Exception("429 quota exceeded")
        response = test_client.post("/api/video/generate", json={"prompt": "test"})
        assert response.status_code == 429
        assert response.json()["error"] is not None

    def test_generate_safety_block_returns_422(self, test_client, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = Exception("safety block")
        response = test_client.post("/api/video/generate", json={"prompt": "test"})
        assert response.status_code == 422

    def test_generate_generic_error_returns_502(self, test_client, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = Exception("network timeout")
        response = test_client.post("/api/video/generate", json={"prompt": "test"})
        assert response.status_code == 502
