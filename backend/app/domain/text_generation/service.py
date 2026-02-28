from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import NoReturn

from google import genai
from google.genai import types

from app.config import settings
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from app.prompt_manager import get_prompt_manager
from app.shared.multimodal import base64_to_part
from app.domain.text_generation.schemas import (
    TextGenerationRequest,
    TextGenerationResponse,
    StructuredGenerationRequest,
)


class GeminiTextService:
    def __init__(self, client: genai.Client) -> None:
        self._client = client
        self._model = settings.TEXT_MODEL
        self._pm = get_prompt_manager()

    def _resolve_system_instruction(self, key: str | None) -> str | None:
        if key is None:
            return None
        return self._pm.get_system_instruction(key)

    def _build_contents(self, request: TextGenerationRequest) -> list[types.Part] | str:
        if not request.parts:
            return request.prompt
        contents = []
        for p in request.parts:
            contents.append(base64_to_part(p.data, p.mime_type))
        contents.append(types.Part.from_text(text=request.prompt))
        return contents

    def _build_config(self, request: TextGenerationRequest, **overrides) -> types.GenerateContentConfig:
        params = {
            "temperature": request.temperature,
            "max_output_tokens": request.max_output_tokens,
        }
        si = self._resolve_system_instruction(request.system_instruction_key)
        if si:
            params["system_instruction"] = si
        params.update(overrides)
        return types.GenerateContentConfig(**params)

    def _handle_error(self, exc: Exception) -> NoReturn:
        err_str = str(exc).lower()
        if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
            raise QuotaExceededError() from exc
        if "safety" in err_str or "block" in err_str:
            raise SafetyBlockError() from exc
        raise GeminiAPIError(str(exc)) from exc

    async def generate(self, request: TextGenerationRequest) -> TextGenerationResponse:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=self._build_contents(request),
                config=self._build_config(request),
            )
            usage = None
            if response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "candidates_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }
            return TextGenerationResponse(text=response.text or "", usage_metadata=usage)
        except (QuotaExceededError, SafetyBlockError):
            raise
        except Exception as exc:
            self._handle_error(exc)

    async def generate_structured(self, request: StructuredGenerationRequest) -> dict:
        import json
        try:
            config = self._build_config(
                request,
                response_mime_type="application/json",
                response_schema=request.response_schema,
            )
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=self._build_contents(request),
                config=config,
            )
            text = response.text or "{}"
            # Strip markdown code fences if present
            text = text.strip()
            if text.startswith("```json"):
                text = text.removeprefix("```json").removesuffix("```").strip()
            elif text.startswith("```"):
                text = text.removeprefix("```").removesuffix("```").strip()
            return json.loads(text)
        except (QuotaExceededError, SafetyBlockError):
            raise
        except json.JSONDecodeError as exc:
            raise GeminiAPIError(f"Failed to parse structured response: {exc}") from exc
        except Exception as exc:
            self._handle_error(exc)

    async def generate_stream(self, request: TextGenerationRequest) -> AsyncGenerator[str, None]:
        try:
            async for chunk in self._client.aio.models.generate_content_stream(
                model=self._model,
                contents=self._build_contents(request),
                config=self._build_config(request),
            ):
                if chunk.text:
                    yield chunk.text
        except (QuotaExceededError, SafetyBlockError):
            raise
        except Exception as exc:
            self._handle_error(exc)
