"""Tests for video generation service and router."""
from __future__ import annotations

import base64
from unittest.mock import MagicMock

import pytest

from app.domain.video_generation.schemas import (
    VideoGenerationRequest,
    VideoReferenceImage,
    ImagePart,
)
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
# Service: generate (async)
# ---------------------------------------------------------------------------

class TestGeminiVideoServiceGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_video_base64(self, mock_genai_client):
        video_bytes = b"test-video-content"
        operation = _make_completed_operation(video_bytes)
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        request = VideoGenerationRequest(prompt="A sunset over the ocean")
        result = await service.generate(request)

        expected_b64 = base64.b64encode(video_bytes).decode("utf-8")
        assert result.video_base64 == expected_b64
        assert result.mime_type == "video/mp4"

    @pytest.mark.asyncio
    async def test_generate_polls_until_done(self, mock_genai_client):
        video_bytes = b"polled-video"
        initial, completed = _make_polling_operation(video_bytes)
        mock_genai_client.models.generate_videos.return_value = initial
        mock_genai_client.operations.get.return_value = completed

        service = _make_service(mock_genai_client)
        request = VideoGenerationRequest(prompt="A cat playing")
        result = await service.generate(request)

        mock_genai_client.operations.get.assert_called_once_with(initial)
        expected_b64 = base64.b64encode(video_bytes).decode("utf-8")
        assert result.video_base64 == expected_b64

    @pytest.mark.asyncio
    async def test_generate_passes_aspect_ratio(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        request = VideoGenerationRequest(prompt="test", aspect_ratio="9:16")
        await service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        config = call_kwargs.kwargs.get("config")
        assert config.aspect_ratio == "9:16"

    @pytest.mark.asyncio
    async def test_generate_passes_negative_prompt(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        request = VideoGenerationRequest(prompt="test", negative_prompt="blurry")
        await service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        config = call_kwargs.kwargs.get("config")
        assert config.negative_prompt == "blurry"

    @pytest.mark.asyncio
    async def test_generate_raises_quota_exceeded_on_429(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = Exception("429 quota exceeded")
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            await service.generate(VideoGenerationRequest(prompt="test"))

    @pytest.mark.asyncio
    async def test_generate_raises_quota_exceeded_on_resource_exhausted(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = Exception("RESOURCE_EXHAUSTED")
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            await service.generate(VideoGenerationRequest(prompt="test"))

    @pytest.mark.asyncio
    async def test_generate_raises_safety_block(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = Exception("safety block triggered")
        service = _make_service(mock_genai_client)
        with pytest.raises(SafetyBlockError):
            await service.generate(VideoGenerationRequest(prompt="test"))

    @pytest.mark.asyncio
    async def test_generate_raises_gemini_api_error_on_generic_exception(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = Exception("network timeout")
        service = _make_service(mock_genai_client)
        with pytest.raises(GeminiAPIError):
            await service.generate(VideoGenerationRequest(prompt="test"))

    @pytest.mark.asyncio
    async def test_generate_re_raises_quota_exceeded_without_wrapping(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = QuotaExceededError()
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            await service.generate(VideoGenerationRequest(prompt="test"))

    @pytest.mark.asyncio
    async def test_generate_re_raises_safety_block_without_wrapping(self, mock_genai_client):
        mock_genai_client.models.generate_videos.side_effect = SafetyBlockError()
        service = _make_service(mock_genai_client)
        with pytest.raises(SafetyBlockError):
            await service.generate(VideoGenerationRequest(prompt="test"))


# ---------------------------------------------------------------------------
# Service: reference images
# ---------------------------------------------------------------------------

class TestVideoServiceReferenceImages:
    @pytest.mark.asyncio
    async def test_single_reference_image(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        img_data = base64.b64encode(b"ref-image").decode()
        request = VideoGenerationRequest(
            prompt="test",
            reference_images=[VideoReferenceImage(data=img_data, mime_type="image/jpeg")],
        )
        await service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        config = call_kwargs.kwargs["config"]
        assert len(config.reference_images) == 1

    @pytest.mark.asyncio
    async def test_multiple_reference_images(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        refs = [
            VideoReferenceImage(data=base64.b64encode(b"img1").decode(), mime_type="image/jpeg"),
            VideoReferenceImage(data=base64.b64encode(b"img2").decode(), mime_type="image/png"),
            VideoReferenceImage(data=base64.b64encode(b"img3").decode(), mime_type="image/jpeg"),
        ]
        request = VideoGenerationRequest(prompt="test", reference_images=refs)
        await service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        config = call_kwargs.kwargs["config"]
        assert len(config.reference_images) == 3

    @pytest.mark.asyncio
    async def test_no_reference_images_omits_config_field(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        request = VideoGenerationRequest(prompt="test")
        await service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        config = call_kwargs.kwargs["config"]
        assert not hasattr(config, "reference_images") or config.reference_images is None

    def test_max_three_reference_images_schema_validation(self):
        refs = [
            VideoReferenceImage(data=base64.b64encode(b"img").decode(), mime_type="image/jpeg")
            for _ in range(4)
        ]
        with pytest.raises(Exception):
            VideoGenerationRequest(prompt="test", reference_images=refs)


# ---------------------------------------------------------------------------
# Service: first & last frame
# ---------------------------------------------------------------------------

class TestVideoServiceFrames:
    @pytest.mark.asyncio
    async def test_first_frame_passed_as_image_kwarg(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        frame_data = base64.b64encode(b"first-frame").decode()
        request = VideoGenerationRequest(
            prompt="test",
            first_frame=ImagePart(data=frame_data, mime_type="image/png"),
        )
        await service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        assert "image" in call_kwargs.kwargs

    @pytest.mark.asyncio
    async def test_last_frame_passed_in_config(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        frame_data = base64.b64encode(b"last-frame").decode()
        request = VideoGenerationRequest(
            prompt="test",
            last_frame=ImagePart(data=frame_data, mime_type="image/png"),
        )
        await service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        config = call_kwargs.kwargs["config"]
        assert config.last_frame is not None

    @pytest.mark.asyncio
    async def test_both_frames_for_interpolation(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        first_data = base64.b64encode(b"first").decode()
        last_data = base64.b64encode(b"last").decode()
        request = VideoGenerationRequest(
            prompt="Interpolate between frames",
            first_frame=ImagePart(data=first_data, mime_type="image/png"),
            last_frame=ImagePart(data=last_data, mime_type="image/png"),
        )
        result = await service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        assert "image" in call_kwargs.kwargs
        assert call_kwargs.kwargs["config"].last_frame is not None
        assert result.video_base64 is not None

    @pytest.mark.asyncio
    async def test_no_frames_omits_image_kwarg(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        request = VideoGenerationRequest(prompt="test")
        await service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        assert "image" not in call_kwargs.kwargs


# ---------------------------------------------------------------------------
# Service: scene extension
# ---------------------------------------------------------------------------

class TestVideoServiceSceneExtension:
    @pytest.mark.asyncio
    async def test_extend_video_passes_video_kwarg(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        prev_video = base64.b64encode(b"previous-video-data").decode()
        request = VideoGenerationRequest(
            prompt="Continue the scene into the garden",
            extend_video_base64=prev_video,
        )
        await service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        assert "video" in call_kwargs.kwargs

    @pytest.mark.asyncio
    async def test_no_extend_omits_video_kwarg(self, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        request = VideoGenerationRequest(prompt="test")
        await service.generate(request)

        call_kwargs = mock_genai_client.models.generate_videos.call_args
        assert "video" not in call_kwargs.kwargs

    @pytest.mark.asyncio
    async def test_extend_video_returns_new_video(self, mock_genai_client):
        extended_bytes = b"extended-video-output"
        operation = _make_completed_operation(extended_bytes)
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        prev_video = base64.b64encode(b"prev").decode()
        request = VideoGenerationRequest(
            prompt="Continue",
            extend_video_base64=prev_video,
        )
        result = await service.generate(request)

        expected_b64 = base64.b64encode(extended_bytes).decode("utf-8")
        assert result.video_base64 == expected_b64


# ---------------------------------------------------------------------------
# Service: timeout guard
# ---------------------------------------------------------------------------

class TestVideoServiceTimeout:
    @pytest.mark.asyncio
    async def test_generate_raises_on_timeout(self, mock_genai_client, monkeypatch):
        import app.domain.video_generation.service as svc_module
        monkeypatch.setattr(svc_module, "_MAX_POLL_SECONDS", 0)

        never_done = MagicMock()
        never_done.done = False
        mock_genai_client.models.generate_videos.return_value = never_done
        mock_genai_client.operations.get.return_value = never_done

        service = _make_service(mock_genai_client)
        with pytest.raises(GeminiAPIError, match="timed out"):
            await service.generate(VideoGenerationRequest(prompt="test"))

    @pytest.mark.asyncio
    async def test_generate_raises_on_empty_results(self, mock_genai_client):
        operation = MagicMock()
        operation.done = True
        operation.response.generated_videos = []
        mock_genai_client.models.generate_videos.return_value = operation

        service = _make_service(mock_genai_client)
        with pytest.raises(GeminiAPIError, match="no results"):
            await service.generate(VideoGenerationRequest(prompt="test"))


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

    def test_generate_with_reference_images(self, test_client, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation
        img_data = base64.b64encode(b"ref").decode()
        response = test_client.post(
            "/api/video/generate",
            json={
                "prompt": "test",
                "reference_images": [{"data": img_data, "mime_type": "image/jpeg"}],
            },
        )
        assert response.status_code == 200

    def test_generate_with_first_frame(self, test_client, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation
        frame_data = base64.b64encode(b"frame").decode()
        response = test_client.post(
            "/api/video/generate",
            json={
                "prompt": "test",
                "first_frame": {"data": frame_data, "mime_type": "image/png"},
            },
        )
        assert response.status_code == 200

    def test_generate_with_scene_extension(self, test_client, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation
        video_data = base64.b64encode(b"prev-video").decode()
        response = test_client.post(
            "/api/video/generate",
            json={
                "prompt": "Continue the scene",
                "extend_video_base64": video_data,
            },
        )
        assert response.status_code == 200

    def test_generate_with_all_features(self, test_client, mock_genai_client):
        operation = _make_completed_operation()
        mock_genai_client.models.generate_videos.return_value = operation
        img_data = base64.b64encode(b"img").decode()
        frame_data = base64.b64encode(b"frame").decode()
        response = test_client.post(
            "/api/video/generate",
            json={
                "prompt": "Full featured request",
                "aspect_ratio": "9:16",
                "negative_prompt": "blurry",
                "reference_images": [
                    {"data": img_data, "mime_type": "image/jpeg"},
                    {"data": img_data, "mime_type": "image/png"},
                ],
                "first_frame": {"data": frame_data, "mime_type": "image/png"},
                "last_frame": {"data": frame_data, "mime_type": "image/png"},
            },
        )
        assert response.status_code == 200

    def test_too_many_reference_images_returns_422(self, test_client):
        img_data = base64.b64encode(b"img").decode()
        response = test_client.post(
            "/api/video/generate",
            json={
                "prompt": "test",
                "reference_images": [
                    {"data": img_data, "mime_type": "image/jpeg"},
                    {"data": img_data, "mime_type": "image/jpeg"},
                    {"data": img_data, "mime_type": "image/jpeg"},
                    {"data": img_data, "mime_type": "image/jpeg"},
                ],
            },
        )
        assert response.status_code == 422
