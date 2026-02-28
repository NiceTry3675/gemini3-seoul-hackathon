from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from google import genai

from app.exceptions import GeminiAPIError, QuotaExceededError, SafetyBlockError
from app.shared.client import get_genai_client
from app.domain.scene_parser.schemas import NovelInput
from app.domain.scene_parser.service import SceneParserService
from app.domain.character_gen.schemas import CharacterGenRequest
from app.domain.character_gen.service import CharacterGenService
from app.domain.cut_planner.schemas import CutPlanRequest, CutPlan
from app.domain.cut_planner.service import CutPlannerService
from app.domain.validator.schemas import ValidationRequest, ValidationReport
from app.domain.validator.service import ValidatorService
from app.domain.image_generation.schemas import ImageGenerationRequest
from app.domain.image_generation.service import GeminiImageService
from app.domain.conti.schemas import (
    ContiRequest,
    ContiResult,
    GeneratedCut,
    PipelineProgress,
)

logger = logging.getLogger(__name__)

_BATCH_SIZE = 3
_BATCH_DELAY = 2.0
_IMAGE_MAX_RETRIES = 3


class ContiOrchestratorService:
    def __init__(self, client: genai.Client) -> None:
        self._client = client
        self._scene_parser = SceneParserService(client)
        self._char_gen = CharacterGenService(client)
        self._cut_planner = CutPlannerService(client)
        self._validator = ValidatorService(client)
        self._image_gen = GeminiImageService(client)

    def _sse_event(self, event: str, data: dict) -> dict:
        return {"event": event, "data": json.dumps(data, ensure_ascii=False)}

    def _progress_event(self, step: int, step_name: str, status: str, detail: str | None = None) -> dict:
        progress = PipelineProgress(step=step, step_name=step_name, status=status, detail=detail)
        return self._sse_event("progress", progress.model_dump())

    async def _generate_image_with_retry(self, cut_prompt: str, cut_number: int) -> tuple[str, str]:
        """Returns (image_base64, mime_type). Returns ("", "image/png") on total failure."""
        for attempt in range(1, _IMAGE_MAX_RETRIES + 1):
            try:
                req = ImageGenerationRequest(prompt=cut_prompt)
                resp = await asyncio.to_thread(self._image_gen.generate, req)
                return resp.image_base64, resp.mime_type
            except Exception as exc:
                logger.warning(
                    "Image gen attempt %d/%d failed for cut %d: %s",
                    attempt, _IMAGE_MAX_RETRIES, cut_number, exc,
                )
                if attempt < _IMAGE_MAX_RETRIES:
                    await asyncio.sleep(1.0)
        return "", "image/png"

    async def generate(self, request: ContiRequest) -> AsyncGenerator[dict, None]:
        novel_input = NovelInput(
            manuscript=request.manuscript,
            genre=request.genre,
            tone=request.tone,
            output_language=request.output_language,
        )

        # Step 1: Scene parsing
        yield self._progress_event(1, "scene_parse", "running")
        try:
            scene_breakdown = await asyncio.to_thread(self._scene_parser.parse, novel_input)
        except Exception as exc:
            yield self._progress_event(1, "scene_parse", "failed", str(exc))
            return
        yield self._progress_event(1, "scene_parse", "completed", f"{len(scene_breakdown.scenes)} scenes parsed")

        # Step 2: Character generation
        yield self._progress_event(2, "character_gen", "running")
        try:
            char_req = CharacterGenRequest(novel_input=novel_input, scene_breakdown=scene_breakdown)
            char_resp = await asyncio.to_thread(self._char_gen.generate, char_req)
            character_sheet = char_resp.character_sheet
        except Exception as exc:
            yield self._progress_event(2, "character_gen", "failed", str(exc))
            return
        yield self._progress_event(2, "character_gen", "completed", f"{len(character_sheet.characters)} characters generated")

        # Step 3: Cut planning
        yield self._progress_event(3, "cut_plan", "running")
        try:
            cut_req = CutPlanRequest(
                novel_input=novel_input,
                scene_breakdown=scene_breakdown,
                character_sheet=character_sheet,
            )
            cut_plan = await asyncio.to_thread(self._cut_planner.plan, cut_req)
        except Exception as exc:
            yield self._progress_event(3, "cut_plan", "failed", str(exc))
            return
        yield self._progress_event(3, "cut_plan", "completed", f"{len(cut_plan.cuts)} cuts planned")

        # Step 4: Validation (with one retry of cut_plan if invalid)
        yield self._progress_event(4, "validate", "running")
        validation_report: ValidationReport | None = None
        try:
            val_req = ValidationRequest(cut_plan=cut_plan, character_sheet=character_sheet)
            validation_report = await asyncio.to_thread(self._validator.validate, val_req)

            if not validation_report.is_valid:
                # Retry cut_plan once
                logger.info("Validation failed, retrying cut plan. Issues: %s", validation_report.summary)
                try:
                    cut_plan = await asyncio.to_thread(self._cut_planner.plan, cut_req)
                    val_req2 = ValidationRequest(cut_plan=cut_plan, character_sheet=character_sheet)
                    validation_report = await asyncio.to_thread(self._validator.validate, val_req2)
                    if not validation_report.is_valid:
                        logger.warning("Validation still failed after retry; proceeding with warning.")
                        yield self._progress_event(4, "validate", "completed", "validation warnings: " + validation_report.summary)
                    else:
                        yield self._progress_event(4, "validate", "completed", "validated after retry")
                except Exception as retry_exc:
                    logger.warning("Cut plan retry failed: %s; proceeding anyway.", retry_exc)
                    yield self._progress_event(4, "validate", "completed", "retry failed; proceeding with original plan")
            else:
                yield self._progress_event(4, "validate", "completed", validation_report.summary)
        except (QuotaExceededError, SafetyBlockError):
            raise
        except Exception as exc:
            logger.warning("Validation step failed: %s; proceeding without validation.", exc)
            yield self._progress_event(4, "validate", "completed", "validation skipped due to error")

        # Step 5: Image generation in batches
        yield self._progress_event(5, "image_gen", "running", f"generating {len(cut_plan.cuts)} images")
        generated_cuts: list[GeneratedCut] = []
        cuts = cut_plan.cuts

        for batch_start in range(0, len(cuts), _BATCH_SIZE):
            batch = cuts[batch_start: batch_start + _BATCH_SIZE]
            tasks = [
                self._generate_image_with_retry(cut.image_prompt, cut.cut_number)
                for cut in batch
            ]
            results = await asyncio.gather(*tasks)

            for cut, (image_base64, mime_type) in zip(batch, results):
                generated_cuts.append(GeneratedCut(
                    cut_number=cut.cut_number,
                    image_base64=image_base64,
                    mime_type=mime_type,
                    dialogue=cut.dialogue,
                    narration=cut.narration,
                    description=cut.description,
                ))

            batch_end = min(batch_start + _BATCH_SIZE, len(cuts))
            yield self._progress_event(
                5, "image_gen", "running",
                f"generated {batch_end}/{len(cuts)} images",
            )

            if batch_end < len(cuts):
                await asyncio.sleep(_BATCH_DELAY)

        yield self._progress_event(5, "image_gen", "completed", f"{len(generated_cuts)} images generated")

        # Final result
        result = ContiResult(
            characters=character_sheet,
            cuts=generated_cuts,
            validation_report=validation_report,
        )
        yield self._sse_event("result", result.model_dump())
