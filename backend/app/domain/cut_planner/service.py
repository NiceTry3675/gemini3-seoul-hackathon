from __future__ import annotations

import json
from typing import NoReturn

from google import genai
from google.genai import types

from app.config import settings
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from app.prompt_manager import get_prompt_manager
from app.domain.cut_planner.schemas import CutPlanRequest, CutPlan


class CutPlannerService:
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

    async def plan(self, request: CutPlanRequest) -> CutPlan:
        try:
            system_instruction = self._pm.get_system_instruction("cut_planner.instruction")

            scenes_summary = "\n".join(
                f"Scene {s.scene_number} - {s.title}: {s.summary} "
                f"(mood: {s.mood}, characters: {', '.join(s.characters)})"
                for s in request.scene_breakdown.scenes
            )
            characters_summary = "\n".join(
                f"- {c.name}: {c.appearance} | {c.personality}"
                for c in request.character_sheet.characters
            )
            user_prompt = (
                f"Genre: {request.novel_input.genre}\n"
                f"Tone: {request.novel_input.tone}\n"
                f"Output language: {request.novel_input.output_language}\n\n"
                f"Scene breakdown:\n{scenes_summary}\n\n"
                f"Characters:\n{characters_summary}\n\n"
                "Create EXACTLY 9 cuts that tell the story visually. "
                "Each cut must have a unique cut_number from 1 to 9."
            )

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=CutPlan,
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
            return CutPlan.model_validate(data)

        except (QuotaExceededError, SafetyBlockError):
            raise
        except json.JSONDecodeError as exc:
            raise GeminiAPIError(f"Failed to parse cut plan response: {exc}") from exc
        except Exception as exc:
            self._handle_error(exc)
