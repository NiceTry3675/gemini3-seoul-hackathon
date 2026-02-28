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
from app.domain.video_generation.schemas import VideoGenerationRequest
from app.domain.video_generation.service import GeminiVideoService
from app.domain.conti.schemas import (
    ContiRequest,
    ContiResult,
    GeneratedCut,
    GenerateMediaRequest,
    GenerateMediaResponse,
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
        self._video_gen = GeminiVideoService(client)

    def _sse_event(self, event: str, data: dict) -> dict:
        return {"event": event, "data": json.dumps(data, ensure_ascii=False)}

    def _progress_event(self, step: int, step_name: str, status: str, detail: str | None = None) -> dict:
        progress = PipelineProgress(step=step, step_name=step_name, status=status, detail=detail)
        return self._sse_event("progress", progress.model_dump())

    async def _generate_image_with_retry(
        self, cut_prompt: str, cut_number: int, reference_images: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        """Returns (image_base64, mime_type). Returns ("", "image/png") on total failure."""
        for attempt in range(1, _IMAGE_MAX_RETRIES + 1):
            try:
                req = ImageGenerationRequest(
                    prompt=cut_prompt,
                    reference_images=reference_images or {},
                )
                resp = await self._image_gen.generate(req)
                return resp.image_base64, resp.mime_type
            except Exception as exc:
                logger.warning(
                    "Image gen attempt %d/%d failed for cut %d: %s",
                    attempt, _IMAGE_MAX_RETRIES, cut_number, exc,
                )
                if attempt < _IMAGE_MAX_RETRIES:
                    await asyncio.sleep(1.0)
        return "", "image/png"

    async def _generate_video_with_retry(self, cut_prompt: str, cut_number: int) -> tuple[str, str]:
        """Returns (video_base64, mime_type). Returns ("", "") on total failure."""
        for attempt in range(1, _IMAGE_MAX_RETRIES + 1):
            try:
                req = VideoGenerationRequest(prompt=cut_prompt)
                resp = await self._video_gen.generate(req)
                return resp.video_base64, resp.mime_type
            except Exception as exc:
                logger.warning(
                    "Video gen attempt %d/%d failed for cut %d: %s",
                    attempt, _IMAGE_MAX_RETRIES, cut_number, exc,
                )
                if attempt < _IMAGE_MAX_RETRIES:
                    await asyncio.sleep(1.0)
        return "", ""

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
            scene_breakdown = await self._scene_parser.parse(novel_input)
        except Exception as exc:
            yield self._progress_event(1, "scene_parse", "failed", str(exc))
            return
        yield self._progress_event(1, "scene_parse", "completed", f"{len(scene_breakdown.scenes)} scenes parsed")

        # Step 2: Character generation
        yield self._progress_event(2, "character_gen", "running")
        reference_images: dict[str, str] = {}
        try:
            char_req = CharacterGenRequest(novel_input=novel_input, scene_breakdown=scene_breakdown)
            char_resp = await self._char_gen.generate(char_req)
            character_sheet = char_resp.character_sheet
            reference_images = char_resp.reference_images
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
            cut_plan = await self._cut_planner.plan(cut_req)
        except Exception as exc:
            yield self._progress_event(3, "cut_plan", "failed", str(exc))
            return
        yield self._progress_event(3, "cut_plan", "completed", f"{len(cut_plan.cuts)} cuts planned")

        # Step 4: Validation (with one retry of cut_plan if invalid)
        yield self._progress_event(4, "validate", "running")
        validation_report: ValidationReport | None = None
        try:
            val_req = ValidationRequest(cut_plan=cut_plan, character_sheet=character_sheet)
            validation_report = await self._validator.validate(val_req)

            if not validation_report.is_valid:
                # Retry cut_plan once
                logger.info("Validation failed, retrying cut plan. Issues: %s", validation_report.summary)
                try:
                    cut_plan = await self._cut_planner.plan(cut_req)
                    val_req2 = ValidationRequest(cut_plan=cut_plan, character_sheet=character_sheet)
                    validation_report = await self._validator.validate(val_req2)
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

        # Step 5: Media generation (image/video/mixed) in batches
        output_mode = request.output_mode
        media_label = "media" if output_mode != "image" else "images"
        yield self._progress_event(5, "media_gen", "running", f"generating {len(cut_plan.cuts)} {media_label}")
        generated_cuts: list[GeneratedCut] = []
        cuts = cut_plan.cuts

        for batch_start in range(0, len(cuts), _BATCH_SIZE):
            batch = cuts[batch_start: batch_start + _BATCH_SIZE]

            batch_results: list[GeneratedCut] = []
            for cut in batch:
                image_base64, mime_type = "", "image/png"
                video_base64, video_mime_type = "", ""

                if output_mode in ("image", "mixed"):
                    image_base64, mime_type = await self._generate_image_with_retry(
                        cut.image_prompt, cut.cut_number, reference_images,
                    )
                if output_mode in ("video", "mixed"):
                    video_base64, video_mime_type = await self._generate_video_with_retry(
                        cut.image_prompt, cut.cut_number,
                    )

                batch_results.append(GeneratedCut(
                    cut_number=cut.cut_number,
                    image_base64=image_base64,
                    mime_type=mime_type,
                    video_base64=video_base64,
                    video_mime_type=video_mime_type,
                    dialogue=cut.dialogue,
                    narration=cut.narration,
                    description=cut.description,
                ))

            generated_cuts.extend(batch_results)

            batch_end = min(batch_start + _BATCH_SIZE, len(cuts))
            yield self._progress_event(
                5, "media_gen", "running",
                f"generated {batch_end}/{len(cuts)} {media_label}",
            )

            if batch_end < len(cuts):
                await asyncio.sleep(_BATCH_DELAY)

        yield self._progress_event(5, "media_gen", "completed", f"{len(generated_cuts)} {media_label} generated")

        # Final result
        result = ContiResult(
            characters=character_sheet,
            cuts=generated_cuts,
            validation_report=validation_report,
            reference_images=reference_images,
        )
        yield self._sse_event("result", result.model_dump())

    async def generate_media_batch(self, request: GenerateMediaRequest) -> GenerateMediaResponse:
        """Generate media (image/video/mixed) for a pre-built cut plan."""
        output_mode = request.output_mode
        ref_images = request.reference_images
        generated_cuts: list[GeneratedCut] = []

        for cut in request.cut_plan.cuts:
            image_base64, mime_type = "", "image/png"
            video_base64, video_mime_type = "", ""

            if output_mode in ("image", "mixed"):
                image_base64, mime_type = await self._generate_image_with_retry(
                    cut.image_prompt, cut.cut_number, ref_images,
                )
            if output_mode in ("video", "mixed"):
                video_base64, video_mime_type = await self._generate_video_with_retry(
                    cut.image_prompt, cut.cut_number,
                )

            generated_cuts.append(GeneratedCut(
                cut_number=cut.cut_number,
                image_base64=image_base64,
                mime_type=mime_type,
                video_base64=video_base64,
                video_mime_type=video_mime_type,
                dialogue=cut.dialogue,
                narration=cut.narration,
                description=cut.description,
            ))

        return GenerateMediaResponse(cuts=generated_cuts)

    async def generate_and_persist(
        self, request: ContiRequest, run_id: str, repo: "PipelineRepository"
    ) -> AsyncGenerator[dict, None]:
        from app.domain.conti.repository import PipelineRepository  # noqa: F811

        result_saved = False
        try:
            async for event in self.generate(request):
                yield event
                try:
                    if event.get("event") == "progress":
                        progress = PipelineProgress.model_validate(
                            json.loads(event["data"])
                        )
                        await repo.save_step(run_id, progress)
                    elif event.get("event") == "result":
                        result_data = json.loads(event["data"])
                        conti_result = ContiResult.model_validate(result_data)
                        await repo.save_result(run_id, conti_result)
                        result_saved = True
                except Exception as exc:
                    logger.warning("DB save failed for run %s: %s", run_id, exc)
        finally:
            if not result_saved:
                try:
                    await repo.mark_failed(run_id, "Pipeline did not produce a result")
                except Exception:
                    pass
