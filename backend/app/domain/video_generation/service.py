from __future__ import annotations

import asyncio
import base64
import time

from google import genai
from google.genai import types

from app.config import settings
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from app.domain.video_generation.schemas import (
    VideoGenerationRequest,
    VideoGenerationResponse,
)

_MAX_POLL_SECONDS = 300
_POLL_INTERVAL = 2


class GeminiVideoService:
    def __init__(self, client: genai.Client) -> None:
        self._client = client
        self._model = settings.VIDEO_MODEL

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        try:
            config = types.GenerateVideosConfig(aspect_ratio=request.aspect_ratio)
            if request.negative_prompt:
                config.negative_prompt = request.negative_prompt
            if request.reference_images:
                config.reference_images = [
                    types.RawReferenceImage(
                        reference_image=types.Image(
                            image_bytes=base64.b64decode(ref.data),
                            mime_type=ref.mime_type,
                        )
                    )
                    for ref in request.reference_images
                ]
            if request.last_frame:
                config.last_frame = types.Image(
                    image_bytes=base64.b64decode(request.last_frame.data),
                    mime_type=request.last_frame.mime_type,
                )

            kwargs: dict = dict(model=self._model, prompt=request.prompt, config=config)

            if request.first_frame:
                kwargs["image"] = types.Image(
                    image_bytes=base64.b64decode(request.first_frame.data),
                    mime_type=request.first_frame.mime_type,
                )
            if request.extend_video_base64:
                kwargs["video"] = types.Video(
                    video_bytes=base64.b64decode(request.extend_video_base64),
                )

            operation = await asyncio.to_thread(
                self._client.models.generate_videos, **kwargs
            )

            start = time.monotonic()
            while not operation.done:
                if time.monotonic() - start > _MAX_POLL_SECONDS:
                    raise GeminiAPIError("Video generation timed out")
                await asyncio.sleep(_POLL_INTERVAL)
                operation = await asyncio.to_thread(
                    self._client.operations.get, operation
                )

            if not operation.response.generated_videos:
                raise GeminiAPIError("Video generation returned no results")

            video = operation.response.generated_videos[0]
            video_b64 = base64.b64encode(video.video.video_bytes).decode("utf-8")
            return VideoGenerationResponse(video_base64=video_b64)
        except (QuotaExceededError, SafetyBlockError):
            raise
        except GeminiAPIError:
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if "429" in msg or "resource_exhausted" in msg:
                raise QuotaExceededError(str(exc)) from exc
            if "safety" in msg or "block" in msg:
                raise SafetyBlockError(str(exc)) from exc
            raise GeminiAPIError(str(exc)) from exc
