"""Tests for image generation service and router."""
from __future__ import annotations

import base64
from unittest.mock import MagicMock

import pytest

from app.domain.image_generation.schemas import ImageGenerationRequest
from app.domain.image_generation.service import GeminiImageService
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(mock_client) -> GeminiImageService:
    return GeminiImageService(mock_client)


def _make_image_response(image_bytes: bytes, mime_type: str = "image/png"):
    """Build a mock response that mimics Gemini image generation output."""
    inline_data = MagicMock()
    inline_data.data = image_bytes
    inline_data.mime_type = mime_type

    part = MagicMock()
    part.inline_data = inline_data

    content = MagicMock()
    content.parts = [part]

    candidate = MagicMock()
    candidate.content = content

    response = MagicMock()
    response.candidates = [candidate]
    return response


def _make_no_image_response():
    """Build a mock response with no inline_data in any part."""
    text_part = MagicMock()
    text_part.inline_data = None

    content = MagicMock()
    content.parts = [text_part]

    candidate = MagicMock()
    candidate.content = content

    response = MagicMock()
    response.candidates = [candidate]
    return response


# ---------------------------------------------------------------------------
# Service: generate
# ---------------------------------------------------------------------------

class TestGeminiImageServiceGenerate:
    def test_generate_returns_base64_image(self, mock_genai_client):
        raw = b"fake png bytes"
        mock_genai_client.models.generate_content.return_value = _make_image_response(raw)
        service = _make_service(mock_genai_client)
        result = service.generate(ImageGenerationRequest(prompt="A cat"))
        expected_b64 = base64.b64encode(raw).decode("utf-8")
        assert result.image_base64 == expected_b64

    def test_generate_returns_correct_mime_type(self, mock_genai_client):
        raw = b"jpeg bytes"
        mock_genai_client.models.generate_content.return_value = _make_image_response(
            raw, mime_type="image/jpeg"
        )
        service = _make_service(mock_genai_client)
        result = service.generate(ImageGenerationRequest(prompt="A dog"))
        assert result.mime_type == "image/jpeg"

    def test_generate_defaults_to_png_when_no_mime(self, mock_genai_client):
        inline_data = MagicMock()
        inline_data.data = b"data"
        inline_data.mime_type = None

        part = MagicMock()
        part.inline_data = inline_data

        content = MagicMock()
        content.parts = [part]

        candidate = MagicMock()
        candidate.content = content

        response = MagicMock()
        response.candidates = [candidate]

        mock_genai_client.models.generate_content.return_value = response
        service = _make_service(mock_genai_client)
        result = service.generate(ImageGenerationRequest(prompt="test"))
        assert result.mime_type == "image/png"

    def test_generate_raises_when_no_image_in_response(self, mock_genai_client):
        mock_genai_client.models.generate_content.return_value = _make_no_image_response()
        service = _make_service(mock_genai_client)
        with pytest.raises(GeminiAPIError, match="No image generated"):
            service.generate(ImageGenerationRequest(prompt="A landscape"))

    def test_generate_raises_quota_exceeded_on_429(self, mock_genai_client):
        mock_genai_client.models.generate_content.side_effect = Exception("429 quota exceeded")
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            service.generate(ImageGenerationRequest(prompt="test"))

    def test_generate_raises_quota_exceeded_on_resource_exhausted(self, mock_genai_client):
        mock_genai_client.models.generate_content.side_effect = Exception("RESOURCE_EXHAUSTED")
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            service.generate(ImageGenerationRequest(prompt="test"))

    def test_generate_raises_safety_block(self, mock_genai_client):
        mock_genai_client.models.generate_content.side_effect = Exception("safety block triggered")
        service = _make_service(mock_genai_client)
        with pytest.raises(SafetyBlockError):
            service.generate(ImageGenerationRequest(prompt="test"))

    def test_generate_raises_gemini_api_error_on_generic_exception(self, mock_genai_client):
        mock_genai_client.models.generate_content.side_effect = Exception("connection error")
        service = _make_service(mock_genai_client)
        with pytest.raises(GeminiAPIError):
            service.generate(ImageGenerationRequest(prompt="test"))

    def test_generate_re_raises_gemini_api_error(self, mock_genai_client):
        mock_genai_client.models.generate_content.side_effect = GeminiAPIError("custom error")
        service = _make_service(mock_genai_client)
        with pytest.raises(GeminiAPIError):
            service.generate(ImageGenerationRequest(prompt="test"))

    def test_generate_with_reference_images_builds_multipart_contents(self, mock_genai_client):
        raw = b"generated image"
        mock_genai_client.models.generate_content.return_value = _make_image_response(raw)
        service = _make_service(mock_genai_client)
        result = service.generate(ImageGenerationRequest(
            prompt="A cat",
            reference_images={"Alice": "cmVmX2RhdGE="},  # base64("ref_data")
        ))
        assert result.image_base64 == base64.b64encode(raw).decode("utf-8")
        # Verify generate_content was called with a list (multipart), not a string
        call_args = mock_genai_client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents") or call_args[1].get("contents")
        assert isinstance(contents, list)

    def test_generate_without_reference_images_uses_string_prompt(self, mock_genai_client):
        raw = b"generated image"
        mock_genai_client.models.generate_content.return_value = _make_image_response(raw)
        service = _make_service(mock_genai_client)
        service.generate(ImageGenerationRequest(prompt="A cat"))
        call_args = mock_genai_client.models.generate_content.call_args
        contents = call_args.kwargs.get("contents") or call_args[1].get("contents")
        assert isinstance(contents, str)

    def test_generate_skips_text_parts_to_find_image(self, mock_genai_client):
        """Parts before the image part have no inline_data."""
        raw = b"image data"
        inline_data = MagicMock()
        inline_data.data = raw
        inline_data.mime_type = "image/png"

        text_part = MagicMock()
        text_part.inline_data = None

        image_part = MagicMock()
        image_part.inline_data = inline_data

        content = MagicMock()
        content.parts = [text_part, image_part]

        candidate = MagicMock()
        candidate.content = content

        response = MagicMock()
        response.candidates = [candidate]
        mock_genai_client.models.generate_content.return_value = response

        service = _make_service(mock_genai_client)
        result = service.generate(ImageGenerationRequest(prompt="test"))
        expected_b64 = base64.b64encode(raw).decode("utf-8")
        assert result.image_base64 == expected_b64


# ---------------------------------------------------------------------------
# Router: POST /api/image/generate
# ---------------------------------------------------------------------------

class TestImageGenerationRouter:
    def test_generate_returns_200_with_base64(self, test_client, mock_genai_client):
        raw = b"png bytes"
        mock_genai_client.models.generate_content.return_value = _make_image_response(raw)
        response = test_client.post(
            "/api/image/generate",
            json={"prompt": "A mountain"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["image_base64"] == base64.b64encode(raw).decode("utf-8")
        assert data["mime_type"] == "image/png"

    def test_generate_missing_prompt_returns_422(self, test_client):
        response = test_client.post("/api/image/generate", json={})
        assert response.status_code == 422

    def test_generate_no_image_returns_502(self, test_client, mock_genai_client):
        mock_genai_client.models.generate_content.return_value = _make_no_image_response()
        response = test_client.post(
            "/api/image/generate",
            json={"prompt": "A landscape"},
        )
        assert response.status_code == 502

    def test_generate_quota_exceeded_returns_429(self, test_client, mock_genai_client):
        mock_genai_client.models.generate_content.side_effect = Exception("429 quota exceeded")
        response = test_client.post("/api/image/generate", json={"prompt": "test"})
        assert response.status_code == 429

    def test_generate_safety_block_returns_422(self, test_client, mock_genai_client):
        mock_genai_client.models.generate_content.side_effect = Exception("safety block")
        response = test_client.post("/api/image/generate", json={"prompt": "test"})
        assert response.status_code == 422

    def test_generate_generic_error_returns_502(self, test_client, mock_genai_client):
        mock_genai_client.models.generate_content.side_effect = Exception("unknown error")
        response = test_client.post("/api/image/generate", json={"prompt": "test"})
        assert response.status_code == 502
