from __future__ import annotations

import json
import logging
from typing import NoReturn

from google import genai
from google.genai import types

from app.config import settings
from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from app.prompt_manager import get_prompt_manager
from app.shared.multimodal import part_to_base64
from app.domain.character_gen.schemas import (
    CharacterGenRequest,
    CharacterGenResponse,
    CharacterSheet,
)

logger = logging.getLogger(__name__)


class CharacterGenService:
    def __init__(self, client: genai.Client) -> None:
        self._client = client
        self._text_model = settings.TEXT_MODEL
        self._image_model = settings.IMAGE_MODEL
        self._pm = get_prompt_manager()

    def _handle_error(self, exc: Exception) -> NoReturn:
        err_str = str(exc).lower()
        if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
            raise QuotaExceededError() from exc
        if "safety" in err_str or "block" in err_str:
            raise SafetyBlockError() from exc
        raise GeminiAPIError(str(exc)) from exc

    async def _generate_character_sheet(self, request: CharacterGenRequest) -> CharacterSheet:
        system_instruction = self._pm.get_system_instruction("character_gen.instruction")

        scenes_summary = "\n".join(
            f"Scene {s.scene_number} - {s.title}: {s.summary} (characters: {', '.join(s.characters)})"
            for s in request.scene_breakdown.scenes
        )
        context_lines: list[str] = [f"Output language: {request.novel_input.output_language}"]
        if request.novel_input.genre and request.novel_input.genre != "unspecified":
            context_lines.append(f"Genre: {request.novel_input.genre}")
        if request.novel_input.tone and request.novel_input.tone != "unspecified":
            context_lines.append(f"Tone: {request.novel_input.tone}")
        context_block = "\n".join(context_lines)

        user_prompt = f"{context_block}\n\nScene breakdown:\n{scenes_summary}"

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=CharacterSheet,
        )

        response = await self._client.aio.models.generate_content(
            model=self._text_model,
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
        return CharacterSheet.model_validate(data)

    async def _generate_reference_image(self, character_name: str, visual_prompt: str) -> str | None:
        try:
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            )
            response = await self._client.aio.models.generate_content(
                model=self._image_model,
                contents=visual_prompt,
                config=config,
            )
            if not response.candidates:
                return None
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                return None
            for part in candidate.content.parts:
                if part.inline_data is not None:
                    return part_to_base64(part)
            return None
        except Exception as exc:
            logger.warning("Reference image generation failed for %s: %s", character_name, exc)
            return None

    async def generate(self, request: CharacterGenRequest) -> CharacterGenResponse:
        try:
            character_sheet = await self._generate_character_sheet(request)
        except (QuotaExceededError, SafetyBlockError):
            raise
        except json.JSONDecodeError as exc:
            raise GeminiAPIError(f"Failed to parse character sheet response: {exc}") from exc
        except Exception as exc:
            self._handle_error(exc)

        reference_images: dict[str, str] = {}
        for character in character_sheet.characters:
            image_b64 = await self._generate_reference_image(character.name, character.visual_prompt)
            if image_b64 is not None:
                reference_images[character.name] = image_b64

        return CharacterGenResponse(
            character_sheet=character_sheet,
            reference_images=reference_images,
        )
