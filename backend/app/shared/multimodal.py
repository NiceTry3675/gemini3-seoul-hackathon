from __future__ import annotations

import base64
from dataclasses import dataclass

from fastapi import UploadFile
from google.genai import types


async def upload_file_to_part(file: UploadFile) -> types.Part:
    """Convert FastAPI UploadFile to GenAI Part."""
    data = await file.read()
    return types.Part.from_bytes(data=data, mime_type=file.content_type or "application/octet-stream")


def base64_to_part(data: str, mime_type: str) -> types.Part:
    """Convert base64 string to GenAI Part."""
    raw = base64.b64decode(data)
    return types.Part.from_bytes(data=raw, mime_type=mime_type)


def part_to_base64(part) -> str:
    """Extract base64 string from GenAI inline_data Part."""
    return base64.b64encode(part.inline_data.data).decode("utf-8")


@dataclass
class GeneratedImage:
    """Image bytes with a pre-built ref_part for chaining into subsequent requests."""
    data: bytes
    mime_type: str
    ref_part: types.Part


def blob_data_to_bytes(blob_data: object) -> bytes:
    if isinstance(blob_data, bytes):
        return blob_data
    if isinstance(blob_data, str):
        return base64.b64decode(blob_data)
    raise RuntimeError(f"Unsupported inline_data.data type: {type(blob_data)!r}")


def part_to_generated_image(part: object) -> GeneratedImage:
    inline = getattr(part, "inline_data", None)
    if inline is None:
        raise RuntimeError("Part has no inline_data")
    data = blob_data_to_bytes(getattr(inline, "data", b""))
    if not data:
        raise RuntimeError("inline_data was empty")
    mime_type = getattr(inline, "mime_type", None) or "image/png"
    return GeneratedImage(
        data=data,
        mime_type=mime_type,
        ref_part=types.Part.from_bytes(data=data, mime_type=mime_type),
    )


def first_image_from_response(resp: types.GenerateContentResponse) -> GeneratedImage:
    """Extract the first image from a Gemini response, with candidate fallback."""
    parts = getattr(resp, "parts", None)
    if parts:
        for part in parts:
            if getattr(part, "inline_data", None) is not None:
                return part_to_generated_image(part)

    for cand in getattr(resp, "candidates", []) or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            if getattr(part, "inline_data", None) is not None:
                return part_to_generated_image(part)

    raise RuntimeError("Image model response contained no image parts")
