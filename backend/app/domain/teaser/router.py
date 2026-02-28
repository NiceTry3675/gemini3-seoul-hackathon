from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends
from google import genai
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.shared.client import get_genai_client
from app.domain.video_generation.service import GeminiVideoService
from app.domain.video_generation.schemas import VideoGenerationRequest, ImagePart

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/teaser", tags=["teaser"])


# ── Request / Response schemas (match frontend contract) ──────────────


class TeaserGenerateRequest(BaseModel):
    source_text: str = Field(..., min_length=1)
    style_template: str = "webtoon_cel"
    output_language: str = "ko"
    max_image_cuts: int = Field(default=9, ge=1, le=9)


class TeaserVideoRequest(BaseModel):
    cuts_base64: list[str] = Field(..., min_length=1)
    story_prompt: str = ""
    aspect_ratio: str = "9:16"
    duration_per_cut: int = 5


# ── POST /api/teaser ──────────────────────────────────────────────────


@router.post("")
async def generate_teaser(
    request: TeaserGenerateRequest,
    client: genai.Client = Depends(get_genai_client),
):
    """Run the 9-cut teaser pipeline and return images.

    Wraps the standalone ``teaser_pipeline.run_teaser`` function which uses
    the *synchronous* Gemini SDK, so we run it in a thread-pool executor to
    avoid blocking the event loop.
    """
    from teaser_models import TeaserRequest as PipelineTeaserRequest
    from teaser_pipeline import run_teaser

    pipeline_req = PipelineTeaserRequest(
        source_text=request.source_text,
        style_template=request.style_template,
        output_language=request.output_language,
        max_image_cuts=request.max_image_cuts,
    )

    result = await asyncio.to_thread(run_teaser, client, pipeline_req)

    return result.model_dump()


# ── POST /api/teaser/video ────────────────────────────────────────────


def _sse_data(payload: dict[str, Any]) -> dict[str, str]:
    return {"data": json.dumps(payload, ensure_ascii=False)}


@router.post("/video")
async def generate_teaser_video(
    request: TeaserVideoRequest,
    client: genai.Client = Depends(get_genai_client),
):
    """Generate a video from teaser cut images.

    Streams SSE events with ``progress``, ``result``, and ``error`` types
    that the frontend ``startVideoGeneration`` function understands.

    For each cut image the Veo model is called with the image as the first
    frame.  The resulting clips are returned individually; if only one cut
    is provided a single video is generated.
    """

    async def event_stream():
        video_service = GeminiVideoService(client)

        def _strip_data_url(b64: str) -> str:
            if b64.startswith("data:"):
                return b64.split(",", 1)[-1]
            return b64

        # Use the first cut as first_frame, last cut as last_frame
        first_b64 = _strip_data_url(request.cuts_base64[0])
        if not first_b64:
            yield _sse_data({"type": "error", "message": "First cut image is empty."})
            return

        last_b64 = _strip_data_url(request.cuts_base64[-1]) if len(request.cuts_base64) > 1 else None

        # Build prompt from story + cinematic direction
        base_prompt = (
            "Cinematic teaser video with smooth camera movement, "
            "atmospheric lighting, dramatic pacing, and seamless scene transitions."
        )
        if request.story_prompt.strip():
            prompt = f"{request.story_prompt.strip()}\n\n{base_prompt}"
        else:
            prompt = base_prompt

        yield _sse_data({
            "type": "progress",
            "step": 1,
            "total_steps": 2,
            "message": "Generating teaser video...",
        })

        try:
            video_req = VideoGenerationRequest(
                prompt=prompt,
                aspect_ratio=request.aspect_ratio,
                first_frame=ImagePart(data=first_b64, mime_type="image/png"),
                last_frame=ImagePart(data=last_b64, mime_type="image/png") if last_b64 else None,
            )
            video_resp = await video_service.generate(video_req)

            yield _sse_data({
                "type": "progress",
                "step": 2,
                "total_steps": 2,
                "message": "Video ready!",
            })
            yield _sse_data({
                "type": "result",
                "video_base64": video_resp.video_base64,
                "duration_seconds": request.duration_per_cut,
            })
        except Exception as exc:
            logger.warning("Video generation failed: %s", exc)
            yield _sse_data({
                "type": "error",
                "message": f"Video generation failed: {exc}",
            })

    return EventSourceResponse(event_stream(), media_type="text/event-stream")
