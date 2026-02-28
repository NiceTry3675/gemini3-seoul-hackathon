from __future__ import annotations

import json
from typing import NoReturn

from google import genai
from google.genai import types

from app.config import settings
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from app.prompt_manager import get_prompt_manager
from app.domain.scene_parser.schemas import NovelInput, SceneBreakdown


class SceneParserService:
    def __init__(self, client: genai.Client) -> None:
        self._client = client
        self._model = settings.TEXT_MODEL
        self._pm = get_prompt_manager()

    def _handle_error(self, exc: Exception) -> NoReturn:
        err_str = str(exc).lower()
        if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
            raise QuotaExceededError() from exc
        if "safety" in err_str or "block" in err_str:
            raise SafetyBlockError() from exc
        raise GeminiAPIError(str(exc)) from exc

    async def parse(self, novel_input: NovelInput) -> SceneBreakdown:
        try:
            system_instruction = self._pm.get_system_instruction("scene_parser.instruction")

            user_prompt = (
                f"Genre: {novel_input.genre}\n"
                f"Tone: {novel_input.tone}\n"
                f"Output language: {novel_input.output_language}\n\n"
                f"Manuscript:\n{novel_input.manuscript}"
            )

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=SceneBreakdown,
            )

            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=config,
            )

            text = response.text or "{}"
            text = text.strip()
            if text.startswith("```json"):
                text = text.removeprefix("```json").removesuffix("```").strip()
            elif text.startswith("```"):
                text = text.removeprefix("```").removesuffix("```").strip()

            data = json.loads(text)
            return SceneBreakdown.model_validate(data)

        except (QuotaExceededError, SafetyBlockError):
            raise
        except json.JSONDecodeError as exc:
            raise GeminiAPIError(f"Failed to parse structured response: {exc}") from exc
        except Exception as exc:
            self._handle_error(exc)
