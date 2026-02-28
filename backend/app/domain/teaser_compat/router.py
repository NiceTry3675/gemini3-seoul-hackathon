from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from google import genai

from app.shared.client import get_genai_client
from app.exceptions import GeminiAPIError
from app.domain.character_gen.schemas import Character, CharacterSheet
from app.domain.conti.schemas import ContiRequest, GenerateMediaRequest
from app.domain.conti.service import ContiOrchestratorService
from app.domain.cut_planner.schemas import Cut, CutPlan
from app.domain.teaser_compat.export_artifacts import (
    ImageSnapshot,
    PromptSnapshot,
    save_export_artifacts,
)
from app.domain.teaser_compat.schemas import (
    MainCharacterCompat,
    PanelCompat,
    PromptPreviewCompatResponse,
    PromptPreviewCutCompat,
    TeaserCompatRequest,
    TeaserCompatResponse,
    TeaserCutCompat,
    TeaserPlanCompat,
    TeaserTranslateRequest,
    TeaserTranslateResponse,
)

router = APIRouter(tags=["teaser-compat"])
logger = logging.getLogger(__name__)


def _get_service(client: genai.Client = Depends(get_genai_client)) -> ContiOrchestratorService:
    return ContiOrchestratorService(client)


def _to_conti_request(request: TeaserCompatRequest) -> ContiRequest:
    return ContiRequest(
        manuscript=request.source_text,
        genre=request.genre,
        tone=request.tone,
        output_language=request.output_language,
        output_mode="image",
        style_template=request.style_template,
    )


def _to_plan(
    request: TeaserCompatRequest,
    cut_plan: CutPlan,
    anchor_prompt: str,
    character_sheet,
) -> TeaserPlanCompat:
    lead = character_sheet.characters[0]
    panels = [
        PanelCompat(
            index=cut.cut_number,
            visual=cut.description,
            speech_bubbles=cut.dialogue,
            narration=cut.narration or None,
        )
        for cut in sorted(cut_plan.cuts, key=lambda c: c.cut_number)
    ]

    return TeaserPlanCompat(
        title="Teaser Plan",
        output_language=request.output_language,
        style_template=request.style_template,
        main_character=MainCharacterCompat(
            name=lead.name,
            one_line_role=lead.role,
            visual_keywords=lead.visual_prompt,
        ),
        character_anchor_prompt=anchor_prompt,
        panels=panels,
    )


def _legacy_output_language(value: str) -> str:
    return value if value in {"ko", "en", "ja"} else "ko"


def _build_compat_from_legacy_preview(request: TeaserCompatRequest, legacy_preview) -> PromptPreviewCompatResponse:
    plan = legacy_preview.plan
    character_sheet = CharacterSheet(
        characters=[
            Character(
                name=plan.main_character.name,
                appearance=plan.main_character.visual_keywords,
                personality=plan.main_character.one_line_role,
                role=plan.main_character.one_line_role,
                visual_prompt=plan.main_character.visual_keywords,
            )
        ]
    )
    cut_prompt_by_index = {cut.index: cut.prompt for cut in legacy_preview.cuts}
    cut_plan = CutPlan(
        cuts=[
            Cut(
                cut_number=panel.index,
                scene_ref=panel.index,
                description=panel.visual,
                dialogue=panel.speech_bubbles,
                narration=panel.narration or "",
                camera_angle="auto",
                emotion="teaser",
                image_prompt=cut_prompt_by_index.get(panel.index, panel.visual),
            )
            for panel in sorted(plan.panels, key=lambda p: p.index)
        ]
    )
    compat_plan = TeaserPlanCompat(
        title=plan.title,
        output_language=plan.output_language,
        style_template=plan.style_template,
        main_character=MainCharacterCompat(
            name=plan.main_character.name,
            one_line_role=plan.main_character.one_line_role,
            visual_keywords=plan.main_character.visual_keywords,
        ),
        character_anchor_prompt=plan.character_anchor_prompt,
        panels=[
            PanelCompat(
                index=panel.index,
                visual=panel.visual,
                speech_bubbles=panel.speech_bubbles,
                narration=panel.narration,
            )
            for panel in sorted(plan.panels, key=lambda p: p.index)
        ],
    )
    return PromptPreviewCompatResponse(
        plan=compat_plan,
        anchor_prompt=legacy_preview.anchor_prompt,
        cuts=[
            PromptPreviewCutCompat(
                index=cut.index,
                prompt=cut.prompt,
                reference_inputs=cut.reference_inputs,
            )
            for cut in sorted(legacy_preview.cuts, key=lambda c: c.index)
        ],
        cut_plan=cut_plan,
        character_sheet=character_sheet,
    )


async def _legacy_prompt_preview_fallback(
    request: TeaserCompatRequest,
    client: genai.Client,
) -> PromptPreviewCompatResponse:
    try:
        try:
            from teaser_models import TeaserRequest as LegacyTeaserRequest
            from teaser_pipeline import run_prompt_preview
        except ImportError:
            from backend.teaser_models import TeaserRequest as LegacyTeaserRequest
            from backend.teaser_pipeline import run_prompt_preview

        legacy_request = LegacyTeaserRequest(
            source_text=request.source_text,
            output_language=_legacy_output_language(request.output_language),
            style_template=request.style_template,
            max_image_cuts=request.max_image_cuts,
        )
        legacy_preview = await asyncio.to_thread(run_prompt_preview, client, legacy_request)
        return _build_compat_from_legacy_preview(request, legacy_preview)
    except Exception as exc:
        err_text = str(exc).lower()
        if "503" in err_text or "unavailable" in err_text or "high demand" in err_text:
            raise HTTPException(
                status_code=503,
                detail="Model is temporarily unavailable due to high demand. Please retry shortly.",
            ) from exc
        raise GeminiAPIError(f"Prompt preview fallback failed: {exc}") from exc


@router.post("/api/prompt-preview", response_model=PromptPreviewCompatResponse)
async def prompt_preview(
    request: TeaserCompatRequest,
    service: ContiOrchestratorService = Depends(_get_service),
) -> PromptPreviewCompatResponse:
    logger.info("Using smoke preview flow for /api/prompt-preview")
    return await _legacy_prompt_preview_fallback(request, service._client)


@router.post("/api/teaser", response_model=TeaserCompatResponse)
async def generate_teaser(
    request: TeaserCompatRequest,
    service: ContiOrchestratorService = Depends(_get_service),
) -> TeaserCompatResponse:
    preview = await service.preview(_to_conti_request(request))

    updated_cuts = []
    for cut in sorted(preview.cut_plan.cuts, key=lambda c: c.cut_number):
        override = request.prompt_overrides.get(cut.cut_number)
        prompt = override.strip() if isinstance(override, str) and override.strip() else cut.image_prompt
        updated_cuts.append(cut.model_copy(update={"image_prompt": prompt}))
    updated_cut_plan = CutPlan(cuts=updated_cuts)

    ref_images = dict(request.reference_images)
    anchor_b64 = ""
    if preview.anchor_prompt.strip():
        anchor_b64, _ = await service._generate_image_with_retry(
            preview.anchor_prompt,
            0,
            ref_images,
        )
        if anchor_b64:
            ref_images.setdefault("anchor", anchor_b64)
            lead_name = preview.characters.characters[0].name
            ref_images.setdefault(lead_name, anchor_b64)

    media = await service.generate_media_batch(
        GenerateMediaRequest(
            cut_plan=updated_cut_plan,
            character_sheet=preview.characters,
            output_mode="image",
            style_template=request.style_template,
            reference_images=ref_images,
        )
    )

    plan = _to_plan(request, updated_cut_plan, preview.anchor_prompt, preview.characters)
    sorted_media_cuts = sorted(media.cuts, key=lambda c: c.cut_number)[:request.max_image_cuts]

    cuts = [
        TeaserCutCompat(index=cut.cut_number, image_base64=cut.image_base64)
        for cut in sorted_media_cuts
    ]

    prompt_snapshots = [
        PromptSnapshot(
            cut_number=cut.cut_number,
            raw_prompt=cut.image_prompt,
            styled_prompt=service._build_styled_prompt(cut.image_prompt, request.style_template),
        )
        for cut in sorted(updated_cut_plan.cuts, key=lambda c: c.cut_number)[:request.max_image_cuts]
    ]
    original_snapshots = [
        ImageSnapshot(
            cut_number=cut.cut_number,
            image_base64=cut.image_base64,
            mime_type=cut.mime_type,
        )
        for cut in sorted_media_cuts
    ]

    export_run_id = None
    try:
        export_run_id = save_export_artifacts(
            request_payload=request.model_dump(),
            plan_payload=plan.model_dump(),
            anchor_prompt=preview.anchor_prompt,
            anchor_image_base64=anchor_b64,
            prompt_snapshots=prompt_snapshots,
            original_images=original_snapshots,
        )
    except Exception as exc:
        logger.warning("Failed to save export artifacts: %s", exc)

    return TeaserCompatResponse(
        plan=plan,
        character_anchor_image_base64=anchor_b64,
        cuts=cuts,
        translated_to_language=None,
        export_run_id=export_run_id,
    )


@router.post("/api/teaser/translate", response_model=TeaserTranslateResponse)
async def translate_teaser_images(
    request: TeaserTranslateRequest,
    service: ContiOrchestratorService = Depends(_get_service),
) -> TeaserTranslateResponse:
    source_cuts = sorted(request.cuts, key=lambda c: c.index)
    translated_cuts: list[TeaserCutCompat] = []
    translated_snapshots: list[ImageSnapshot] = []
    original_snapshots: list[ImageSnapshot] = []
    prompt_snapshots: list[PromptSnapshot] = []
    translation_records: list[dict] = []

    for cut in source_cuts:
        translated_b64, translated_mime, prompt_used, used_fallback = await service.translate_cut_text_only(
            image_base64=cut.image_base64,
            mime_type=cut.mime_type,
            source_language=request.source_language,
            target_language=request.target_language,
            cut_number=cut.index,
            dialogue=cut.dialogue,
            narration=cut.narration,
        )
        translated_cuts.append(TeaserCutCompat(index=cut.index, image_base64=translated_b64))
        original_snapshots.append(
            ImageSnapshot(
                cut_number=cut.index,
                image_base64=cut.image_base64,
                mime_type=cut.mime_type,
            )
        )
        translated_snapshots.append(
            ImageSnapshot(
                cut_number=cut.index,
                image_base64=translated_b64,
                mime_type=translated_mime,
            )
        )
        prompt_snapshots.append(
            PromptSnapshot(
                cut_number=cut.index,
                raw_prompt=prompt_used,
                styled_prompt=prompt_used,
            )
        )
        translation_records.append(
            {
                "cut_number": cut.index,
                "used_fallback_original": used_fallback,
                "translation_prompt": prompt_used,
            }
        )

    export_run_id = None
    try:
        export_run_id = save_export_artifacts(
            request_payload=request.model_dump(),
            plan_payload={"title": "Teaser Translation"},
            anchor_prompt="",
            anchor_image_base64="",
            prompt_snapshots=prompt_snapshots,
            original_images=original_snapshots,
            translated_language=request.target_language,
            translated_images=translated_snapshots,
            translation_records=translation_records,
        )
    except Exception as exc:
        logger.warning("Failed to save translation artifacts: %s", exc)

    return TeaserTranslateResponse(
        translated_to_language=request.target_language,
        cuts=translated_cuts,
        export_run_id=export_run_id,
    )
