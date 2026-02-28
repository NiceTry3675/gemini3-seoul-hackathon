from __future__ import annotations

import asyncio
from functools import partial

from fastapi import APIRouter
from pydantic import BaseModel

from app.domain.style_preview.service import generate_style_preview

router = APIRouter(prefix="/api/style-preview", tags=["style-preview"])


class StylePreviewRequest(BaseModel):
    style_template: str
    story_text: str | None = None


class StylePreviewResponse(BaseModel):
    style_template: str
    images: list[str]  # base64 PNG images


@router.post("", response_model=StylePreviewResponse)
async def generate_preview(req: StylePreviewRequest) -> StylePreviewResponse:
    loop = asyncio.get_event_loop()
    images = await loop.run_in_executor(
        None,
        partial(generate_style_preview, req.style_template, req.story_text),
    )
    return StylePreviewResponse(style_template=req.style_template, images=images)
