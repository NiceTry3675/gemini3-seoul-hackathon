"""Tests for app/shared/multimodal.py"""
from __future__ import annotations

import base64
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.shared.multimodal import base64_to_part, part_to_base64, upload_file_to_part


# ---------------------------------------------------------------------------
# Tests: base64_to_part
# ---------------------------------------------------------------------------

class TestBase64ToPart:
    def test_returns_part_with_correct_data(self):
        raw = b"fake image bytes"
        encoded = base64.b64encode(raw).decode("utf-8")
        part = base64_to_part(encoded, "image/png")
        # The Part should have inline_data with the original bytes
        assert part.inline_data.data == raw

    def test_returns_part_with_correct_mime_type(self):
        raw = b"some data"
        encoded = base64.b64encode(raw).decode("utf-8")
        part = base64_to_part(encoded, "image/jpeg")
        assert part.inline_data.mime_type == "image/jpeg"

    def test_empty_bytes(self):
        encoded = base64.b64encode(b"").decode("utf-8")
        part = base64_to_part(encoded, "application/octet-stream")
        assert part.inline_data.data == b""

    def test_invalid_base64_raises(self):
        with pytest.raises(Exception):
            base64_to_part("not-valid-base64!!!", "image/png")


# ---------------------------------------------------------------------------
# Tests: part_to_base64
# ---------------------------------------------------------------------------

class TestPartToBase64:
    def test_round_trip(self):
        raw = b"hello bytes"
        encoded_input = base64.b64encode(raw).decode("utf-8")
        part = base64_to_part(encoded_input, "image/png")
        result = part_to_base64(part)
        assert result == encoded_input

    def test_returns_string(self):
        raw = b"data"
        encoded_input = base64.b64encode(raw).decode("utf-8")
        part = base64_to_part(encoded_input, "image/png")
        result = part_to_base64(part)
        assert isinstance(result, str)

    def test_with_arbitrary_bytes(self):
        raw = bytes(range(256))
        encoded_input = base64.b64encode(raw).decode("utf-8")
        part = base64_to_part(encoded_input, "application/octet-stream")
        result = part_to_base64(part)
        assert base64.b64decode(result) == raw


# ---------------------------------------------------------------------------
# Tests: upload_file_to_part
# ---------------------------------------------------------------------------

class TestUploadFileToPart:
    @pytest.mark.asyncio
    async def test_returns_part_with_file_data(self):
        raw = b"fake file content"
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=raw)
        mock_file.content_type = "image/png"

        part = await upload_file_to_part(mock_file)
        assert part.inline_data.data == raw

    @pytest.mark.asyncio
    async def test_uses_content_type(self):
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=b"data")
        mock_file.content_type = "image/jpeg"

        part = await upload_file_to_part(mock_file)
        assert part.inline_data.mime_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_falls_back_to_octet_stream_when_no_content_type(self):
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=b"data")
        mock_file.content_type = None

        part = await upload_file_to_part(mock_file)
        assert part.inline_data.mime_type == "application/octet-stream"

    @pytest.mark.asyncio
    async def test_empty_file(self):
        mock_file = AsyncMock()
        mock_file.read = AsyncMock(return_value=b"")
        mock_file.content_type = "text/plain"

        part = await upload_file_to_part(mock_file)
        assert part.inline_data.data == b""
