from __future__ import annotations

import asyncio
import base64
import time
from typing import NoReturn

from google import genai
from google.genai import types

from app.config import settings
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from app.shared.multimodal import base64_to_part
from app.domain.video_generation.schemas import (
    VideoGenerationRequest,
    VideoGenerationResponse,
)

_MAX_POLL_SECONDS = 600  # 10분 타임아웃


class GeminiVideoService:
    def __init__(self, client: genai.Client) -> None:
        self._client = client
        self._model = settings.VIDEO_MODEL

    def _handle_error(self, exc: Exception) -> NoReturn:
        err_str = str(exc).lower()
        if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
            raise QuotaExceededError() from exc
        if "safety" in err_str or "block" in err_str:
            raise SafetyBlockError() from exc
        raise GeminiAPIError(str(exc)) from exc

    def _decode_image(self, data: str, mime_type: str) -> types.Image:
        raw = base64.b64decode(data)
        return types.Image(image_bytes=raw, mime_type=mime_type)

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        try:
            config_params: dict = {
                "aspect_ratio": request.aspect_ratio,
                "negative_prompt": request.negative_prompt,
            }

            # Reference images (최대 3장)
            if request.reference_images:
                ref_images = []
                for ref in request.reference_images:
                    ref_images.append(
                        types.VideoGenerationReferenceImage(
                            image=self._decode_image(ref.data, ref.mime_type),
                            reference_type=ref.reference_type,
                        )
                    )
                config_params["reference_images"] = ref_images

            # Last frame (first/last frame interpolation)
            if request.last_frame:
                config_params["last_frame"] = self._decode_image(
                    request.last_frame.data, request.last_frame.mime_type,
                )

            config = types.GenerateVideosConfig(**config_params)

            # Build generate_videos kwargs
            gen_kwargs: dict = {
                "model": self._model,
                "prompt": request.prompt,
                "config": config,
            }

            # First frame
            if request.first_frame:
                gen_kwargs["image"] = self._decode_image(
                    request.first_frame.data, request.first_frame.mime_type,
                )

            # Scene extension (이전 영상 연장)
            if request.extend_video_base64:
                raw_video = base64.b64decode(request.extend_video_base64)
                gen_kwargs["video"] = types.Video(video_bytes=raw_video)

            operation = await self._client.aio.models.generate_videos(**gen_kwargs)

            start = time.monotonic()
            while not operation.done:
                if time.monotonic() - start > _MAX_POLL_SECONDS:
                    raise GeminiAPIError("Video generation timed out")
                await asyncio.sleep(5)
                operation = await self._client.aio.operations.get(operation)

            if not operation.response or not operation.response.generated_videos:
                raise GeminiAPIError("Video generation returned no results")

            video = operation.response.generated_videos[0]
            video_base64 = base64.b64encode(video.video.video_bytes).decode("utf-8")

            return VideoGenerationResponse(video_base64=video_base64)
        except (QuotaExceededError, SafetyBlockError, GeminiAPIError):
            raise
        except Exception as exc:
            self._handle_error(exc)
