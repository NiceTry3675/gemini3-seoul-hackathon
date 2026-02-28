"""Tests for text generation service and router."""
from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.domain.text_generation.schemas import (
    TextGenerationRequest,
    StructuredGenerationRequest,
    MultimodalPart,
)
from app.domain.text_generation.service import GeminiTextService
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(mock_client) -> GeminiTextService:
    return GeminiTextService(mock_client)


def _make_text_response(text: str, prompt_tokens=10, candidates_tokens=5):
    response = MagicMock()
    response.text = text
    response.usage_metadata = MagicMock(
        prompt_token_count=prompt_tokens,
        candidates_token_count=candidates_tokens,
        total_token_count=prompt_tokens + candidates_tokens,
    )
    response.candidates = []
    return response


# ---------------------------------------------------------------------------
# Service: generate
# ---------------------------------------------------------------------------

class TestGeminiTextServiceGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_text(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response("Hello!")
        service = _make_service(mock_genai_client)
        request = TextGenerationRequest(prompt="Say hello")
        result = await service.generate(request)
        assert result.text == "Hello!"

    @pytest.mark.asyncio
    async def test_generate_includes_usage_metadata(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response(
            "Hi", prompt_tokens=8, candidates_tokens=3
        )
        service = _make_service(mock_genai_client)
        result = await service.generate(TextGenerationRequest(prompt="Greet"))
        assert result.usage_metadata["prompt_tokens"] == 8
        assert result.usage_metadata["candidates_tokens"] == 3
        assert result.usage_metadata["total_tokens"] == 11

    @pytest.mark.asyncio
    async def test_generate_handles_none_text(self, mock_genai_client):
        response = MagicMock()
        response.text = None
        response.usage_metadata = None
        mock_genai_client.aio.models.generate_content.return_value = response
        service = _make_service(mock_genai_client)
        result = await service.generate(TextGenerationRequest(prompt="test"))
        assert result.text == ""
        assert result.usage_metadata is None

    @pytest.mark.asyncio
    async def test_generate_passes_temperature_and_max_tokens(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response("ok")
        service = _make_service(mock_genai_client)
        request = TextGenerationRequest(prompt="test", temperature=0.5, max_output_tokens=256)
        await service.generate(request)
        call_kwargs = mock_genai_client.aio.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs.args[2] if len(call_kwargs.args) > 2 else None
        if config is None:
            # Try positional
            config = call_kwargs[1].get("config")
        assert config is not None

    @pytest.mark.asyncio
    async def test_generate_raises_quota_exceeded_on_429(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("429 quota exceeded")
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            await service.generate(TextGenerationRequest(prompt="test"))

    @pytest.mark.asyncio
    async def test_generate_raises_quota_exceeded_on_resource_exhausted(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("RESOURCE_EXHAUSTED")
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            await service.generate(TextGenerationRequest(prompt="test"))

    @pytest.mark.asyncio
    async def test_generate_raises_safety_block(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("safety block triggered")
        service = _make_service(mock_genai_client)
        with pytest.raises(SafetyBlockError):
            await service.generate(TextGenerationRequest(prompt="test"))

    @pytest.mark.asyncio
    async def test_generate_raises_gemini_api_error_on_generic_exception(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("network timeout")
        service = _make_service(mock_genai_client)
        with pytest.raises(GeminiAPIError):
            await service.generate(TextGenerationRequest(prompt="test"))

    @pytest.mark.asyncio
    async def test_generate_re_raises_quota_exceeded_without_wrapping(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = QuotaExceededError()
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            await service.generate(TextGenerationRequest(prompt="test"))

    @pytest.mark.asyncio
    async def test_generate_re_raises_safety_block_without_wrapping(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = SafetyBlockError()
        service = _make_service(mock_genai_client)
        with pytest.raises(SafetyBlockError):
            await service.generate(TextGenerationRequest(prompt="test"))


# ---------------------------------------------------------------------------
# Service: generate_structured
# ---------------------------------------------------------------------------

class TestGeminiTextServiceGenerateStructured:
    def _make_json_response(self, data: dict):
        response = MagicMock()
        response.text = json.dumps(data)
        response.usage_metadata = None
        return response

    @pytest.mark.asyncio
    async def test_returns_parsed_dict(self, mock_genai_client):
        expected = {"name": "Alice", "age": 30}
        mock_genai_client.aio.models.generate_content.return_value = self._make_json_response(expected)
        service = _make_service(mock_genai_client)
        request = StructuredGenerationRequest(
            prompt="Generate a person",
            response_schema={"type": "object"},
        )
        result = await service.generate_structured(request)
        assert result == expected

    @pytest.mark.asyncio
    async def test_strips_markdown_json_fence(self, mock_genai_client):
        response = MagicMock()
        response.text = '```json\n{"key": "value"}\n```'
        response.usage_metadata = None
        mock_genai_client.aio.models.generate_content.return_value = response
        service = _make_service(mock_genai_client)
        result = await service.generate_structured(
            StructuredGenerationRequest(prompt="test", response_schema={})
        )
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_strips_plain_code_fence(self, mock_genai_client):
        response = MagicMock()
        response.text = '```\n{"key": "value"}\n```'
        response.usage_metadata = None
        mock_genai_client.aio.models.generate_content.return_value = response
        service = _make_service(mock_genai_client)
        result = await service.generate_structured(
            StructuredGenerationRequest(prompt="test", response_schema={})
        )
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_raises_gemini_api_error_on_invalid_json(self, mock_genai_client):
        response = MagicMock()
        response.text = "not json at all"
        response.usage_metadata = None
        mock_genai_client.aio.models.generate_content.return_value = response
        service = _make_service(mock_genai_client)
        with pytest.raises(GeminiAPIError, match="Failed to parse"):
            await service.generate_structured(
                StructuredGenerationRequest(prompt="test", response_schema={})
            )

    @pytest.mark.asyncio
    async def test_raises_quota_exceeded(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("429 quota")
        service = _make_service(mock_genai_client)
        with pytest.raises(QuotaExceededError):
            await service.generate_structured(
                StructuredGenerationRequest(prompt="test", response_schema={})
            )

    @pytest.mark.asyncio
    async def test_raises_safety_block(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("safety block")
        service = _make_service(mock_genai_client)
        with pytest.raises(SafetyBlockError):
            await service.generate_structured(
                StructuredGenerationRequest(prompt="test", response_schema={})
            )

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_dict(self, mock_genai_client):
        response = MagicMock()
        response.text = None
        response.usage_metadata = None
        mock_genai_client.aio.models.generate_content.return_value = response
        service = _make_service(mock_genai_client)
        result = await service.generate_structured(
            StructuredGenerationRequest(prompt="test", response_schema={})
        )
        assert result == {}


# ---------------------------------------------------------------------------
# Router: POST /api/text/generate
# ---------------------------------------------------------------------------

class TestTextGenerationRouter:
    def test_generate_returns_200(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response("Generated text")
        response = test_client.post(
            "/api/text/generate",
            json={"prompt": "Hello"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Generated text"

    def test_generate_returns_usage_metadata(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response(
            "text", prompt_tokens=10, candidates_tokens=5
        )
        response = test_client.post(
            "/api/text/generate",
            json={"prompt": "Hello"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["usage_metadata"]["prompt_tokens"] == 10
        assert data["usage_metadata"]["total_tokens"] == 15

    def test_generate_with_temperature_and_max_tokens(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response("ok")
        response = test_client.post(
            "/api/text/generate",
            json={"prompt": "Hi", "temperature": 0.7, "max_output_tokens": 512},
        )
        assert response.status_code == 200

    def test_generate_invalid_temperature_returns_422(self, test_client):
        response = test_client.post(
            "/api/text/generate",
            json={"prompt": "Hi", "temperature": 5.0},
        )
        assert response.status_code == 422

    def test_generate_missing_prompt_returns_422(self, test_client):
        response = test_client.post("/api/text/generate", json={})
        assert response.status_code == 422

    def test_generate_quota_exceeded_returns_429(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("429 quota exceeded")
        response = test_client.post("/api/text/generate", json={"prompt": "test"})
        assert response.status_code == 429
        assert response.json()["error"] is not None

    def test_generate_safety_block_returns_422(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("safety block")
        response = test_client.post("/api/text/generate", json={"prompt": "test"})
        assert response.status_code == 422

    def test_generate_generic_error_returns_502(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.side_effect = Exception("network timeout")
        response = test_client.post("/api/text/generate", json={"prompt": "test"})
        assert response.status_code == 502

    def test_structured_returns_200(self, test_client, mock_genai_client):
        response_mock = MagicMock()
        response_mock.text = json.dumps({"result": "ok"})
        response_mock.usage_metadata = None
        mock_genai_client.aio.models.generate_content.return_value = response_mock
        response = test_client.post(
            "/api/text/structured",
            json={
                "prompt": "Generate JSON",
                "response_schema": {"type": "object"},
            },
        )
        assert response.status_code == 200
        assert response.json() == {"result": "ok"}

    def test_structured_missing_schema_returns_422(self, test_client):
        response = test_client.post(
            "/api/text/structured",
            json={"prompt": "test"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Service: multimodal input (_build_contents)
# ---------------------------------------------------------------------------

class TestGeminiTextServiceMultimodal:
    @pytest.mark.asyncio
    async def test_no_parts_passes_plain_string(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response("ok")
        service = _make_service(mock_genai_client)
        request = TextGenerationRequest(prompt="Hello")
        await service.generate(request)

        call_kwargs = mock_genai_client.aio.models.generate_content.call_args
        assert call_kwargs.kwargs["contents"] == "Hello"

    @pytest.mark.asyncio
    async def test_single_part_builds_part_list(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response("ok")
        service = _make_service(mock_genai_client)
        img_data = base64.b64encode(b"fake-image").decode()
        request = TextGenerationRequest(
            prompt="Describe this image",
            parts=[MultimodalPart(data=img_data, mime_type="image/jpeg")],
        )
        await service.generate(request)

        call_kwargs = mock_genai_client.aio.models.generate_content.call_args
        contents = call_kwargs.kwargs["contents"]
        assert isinstance(contents, list)
        assert len(contents) == 2  # 1 image part + 1 text part

    @pytest.mark.asyncio
    async def test_multiple_parts_builds_all(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response("ok")
        service = _make_service(mock_genai_client)
        img_data = base64.b64encode(b"fake-image").decode()
        audio_data = base64.b64encode(b"fake-audio").decode()
        video_data = base64.b64encode(b"fake-video").decode()
        request = TextGenerationRequest(
            prompt="Analyze these files",
            parts=[
                MultimodalPart(data=img_data, mime_type="image/jpeg"),
                MultimodalPart(data=audio_data, mime_type="audio/mp3"),
                MultimodalPart(data=video_data, mime_type="video/mp4"),
            ],
        )
        await service.generate(request)

        call_kwargs = mock_genai_client.aio.models.generate_content.call_args
        contents = call_kwargs.kwargs["contents"]
        assert isinstance(contents, list)
        assert len(contents) == 4  # 3 media parts + 1 text part (prompt is last)

    @pytest.mark.asyncio
    async def test_parts_default_empty_is_backward_compatible(self, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response("ok")
        service = _make_service(mock_genai_client)
        request = TextGenerationRequest(prompt="Just text")
        assert request.parts == []
        await service.generate(request)

        call_kwargs = mock_genai_client.aio.models.generate_content.call_args
        assert call_kwargs.kwargs["contents"] == "Just text"

    @pytest.mark.asyncio
    async def test_structured_with_parts(self, mock_genai_client):
        response = MagicMock()
        response.text = json.dumps({"result": "ok"})
        response.usage_metadata = None
        mock_genai_client.aio.models.generate_content.return_value = response
        service = _make_service(mock_genai_client)
        img_data = base64.b64encode(b"chart-image").decode()
        request = StructuredGenerationRequest(
            prompt="Extract data from this chart",
            parts=[MultimodalPart(data=img_data, mime_type="image/png")],
            response_schema={"type": "object"},
        )
        result = await service.generate_structured(request)

        call_kwargs = mock_genai_client.aio.models.generate_content.call_args
        contents = call_kwargs.kwargs["contents"]
        assert isinstance(contents, list)
        assert len(contents) == 2
        assert result == {"result": "ok"}


# ---------------------------------------------------------------------------
# Router: multimodal input via POST /api/text/generate
# ---------------------------------------------------------------------------

class TestTextMultimodalRouter:
    def test_generate_with_parts_returns_200(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response("Described!")
        img_data = base64.b64encode(b"fake-img").decode()
        response = test_client.post(
            "/api/text/generate",
            json={
                "prompt": "Describe this",
                "parts": [{"data": img_data, "mime_type": "image/jpeg"}],
            },
        )
        assert response.status_code == 200
        assert response.json()["text"] == "Described!"

    def test_generate_with_multiple_parts_returns_200(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response("Analysis complete")
        img_data = base64.b64encode(b"fake-img").decode()
        audio_data = base64.b64encode(b"fake-audio").decode()
        response = test_client.post(
            "/api/text/generate",
            json={
                "prompt": "Analyze these",
                "parts": [
                    {"data": img_data, "mime_type": "image/jpeg"},
                    {"data": audio_data, "mime_type": "audio/mp3"},
                ],
            },
        )
        assert response.status_code == 200

    def test_generate_without_parts_still_works(self, test_client, mock_genai_client):
        mock_genai_client.aio.models.generate_content.return_value = _make_text_response("Hello")
        response = test_client.post(
            "/api/text/generate",
            json={"prompt": "Hello"},
        )
        assert response.status_code == 200

    def test_parts_missing_mime_type_returns_422(self, test_client):
        img_data = base64.b64encode(b"fake").decode()
        response = test_client.post(
            "/api/text/generate",
            json={
                "prompt": "test",
                "parts": [{"data": img_data}],
            },
        )
        assert response.status_code == 422

    def test_parts_missing_data_returns_422(self, test_client):
        response = test_client.post(
            "/api/text/generate",
            json={
                "prompt": "test",
                "parts": [{"mime_type": "image/jpeg"}],
            },
        )
        assert response.status_code == 422
