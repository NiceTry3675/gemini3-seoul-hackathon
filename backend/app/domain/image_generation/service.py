from __future__ import annotations

from typing import NoReturn

from google import genai
from google.genai import types

from app.config import settings
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from app.prompt_manager import get_prompt_manager
from app.shared.multimodal import part_to_base64
from app.domain.image_generation.schemas import (
    ImageGenerationRequest,
    ImageGenerationResponse,
)


class GeminiImageService:
    def __init__(self, client: genai.Client) -> None:
        self._client = client
        self._model = settings.IMAGE_MODEL
        self._pm = get_prompt_manager()

    def _resolve_system_instruction(self, key: str | None) -> str | None:
        if key is None:
            return None
        return self._pm.get_system_instruction(key)

    def _handle_error(self, exc: Exception) -> NoReturn:
        err_str = str(exc).lower()
        if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
            raise QuotaExceededError() from exc
        if "safety" in err_str or "block" in err_str:
            raise SafetyBlockError() from exc
        raise GeminiAPIError(str(exc)) from exc

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        try:
            config_params = {
                "response_modalities": ["IMAGE"],
            }
            si = self._resolve_system_instruction(request.system_instruction_key)
            if si:
                config_params["system_instruction"] = si

            response = self._client.models.generate_content(
                model=self._model,
                contents=request.prompt,
                config=types.GenerateContentConfig(**config_params),
            )

            # Extract image from response
            candidate = response.candidates[0]
            image_part = None
            for part in candidate.content.parts:
                if part.inline_data is not None:
                    image_part = part
                    break

            if image_part is None:
                raise GeminiAPIError("No image generated in response")

            return ImageGenerationResponse(
                image_base64=part_to_base64(image_part),
                mime_type=image_part.inline_data.mime_type or "image/png",
            )
        except (QuotaExceededError, SafetyBlockError, GeminiAPIError):
            raise
        except Exception as exc:
            self._handle_error(exc)
