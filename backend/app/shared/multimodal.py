import base64
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
