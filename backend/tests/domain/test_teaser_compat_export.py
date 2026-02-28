from __future__ import annotations

import base64
from unittest.mock import AsyncMock, patch

from app.domain.character_gen.schemas import Character, CharacterSheet
from app.domain.conti.schemas import (
    GenerateMediaResponse,
    GeneratedCut,
    PromptPreviewCut,
    PromptPreviewResult,
)
from app.domain.conti.service import ContiOrchestratorService
from app.domain.cut_planner.schemas import Cut, CutPlan
from app.domain.teaser_compat.export_artifacts import (
    ImageSnapshot,
    PromptSnapshot,
    save_export_artifacts,
)


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def _preview_result() -> PromptPreviewResult:
    character_sheet = CharacterSheet(
        characters=[
            Character(
                name="Alice",
                appearance="brown hair",
                personality="calm",
                role="lead",
                visual_prompt="female lead, brown hair",
            )
        ]
    )
    cuts = [
        Cut(
            cut_number=i,
            scene_ref=1,
            description=f"cut {i}",
            dialogue=[f"line {i}"],
            narration=f"narration {i}",
            camera_angle="close-up",
            emotion="tense",
            image_prompt=f"raw prompt {i}",
        )
        for i in range(1, 10)
    ]
    preview_cuts = [
        PromptPreviewCut(cut_number=i, styled_prompt=f"styled {i}", reference_inputs=["anchor"])
        for i in range(1, 10)
    ]
    return PromptPreviewResult(
        cut_plan=CutPlan(cuts=cuts),
        characters=character_sheet,
        anchor_prompt="anchor prompt",
        cuts=preview_cuts,
    )


def _media_result(prefix: str = "orig") -> GenerateMediaResponse:
    cuts = [
        GeneratedCut(
            cut_number=i,
            image_base64=_b64(f"{prefix}-{i}"),
            mime_type="image/png",
            video_base64="",
            video_mime_type="",
            dialogue=[f"line {i}"],
            narration=f"narration {i}",
            description=f"cut {i}",
        )
        for i in range(1, 10)
    ]
    return GenerateMediaResponse(cuts=cuts)


class TestTeaserCompatExport:
    def test_teaser_without_translation_uses_original_cuts(self, test_client):
        preview = _preview_result()
        media = _media_result("orig")

        with (
            patch.object(ContiOrchestratorService, "preview", new=AsyncMock(return_value=preview)),
            patch.object(
                ContiOrchestratorService,
                "_generate_image_with_retry",
                new=AsyncMock(return_value=(_b64("anchor"), "image/png")),
            ),
            patch.object(ContiOrchestratorService, "generate_media_batch", new=AsyncMock(return_value=media)),
            patch("app.domain.teaser_compat.router.save_export_artifacts", return_value="export_test") as save_mock,
        ):
            response = test_client.post(
                "/api/teaser",
                json={
                    "source_text": "sample",
                    "style_template": "webtoon_cel",
                    "max_image_cuts": 9,
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["translated_to_language"] is None
        assert payload["export_run_id"] == "export_test"
        assert payload["cuts"][0]["image_base64"] == _b64("orig-1")
        save_mock.assert_called_once()

    def test_translate_endpoint_replaces_cut_images(self, test_client):
        async def _translate_side_effect(**kwargs):
            cut_no = kwargs["cut_number"]
            return _b64(f"translated-{cut_no}"), "image/png", f"tp-{cut_no}", False

        with (
            patch.object(
                ContiOrchestratorService,
                "translate_cut_text_only",
                new=AsyncMock(side_effect=_translate_side_effect),
            ) as translate_mock,
            patch("app.domain.teaser_compat.router.save_export_artifacts", return_value="export_test") as save_mock,
        ):
            response = test_client.post(
                "/api/teaser/translate",
                json={
                    "source_language": "ko",
                    "target_language": "en",
                    "cuts": [
                        {
                            "index": i,
                            "image_base64": _b64(f"orig-{i}"),
                            "mime_type": "image/png",
                            "dialogue": [f"line {i}"],
                            "narration": f"narration {i}",
                            "description": f"cut {i}",
                        }
                        for i in range(1, 10)
                    ],
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["translated_to_language"] == "en"
        assert payload["cuts"][0]["image_base64"] == _b64("translated-1")
        assert translate_mock.await_count == 9
        assert save_mock.call_args.kwargs["translated_language"] == "en"
        assert len(save_mock.call_args.kwargs["translated_images"]) == 9

    def test_translate_endpoint_fallback_keeps_original_on_failure(self, test_client):
        async def _translate_side_effect(**kwargs):
            cut_no = kwargs["cut_number"]
            if cut_no == 1:
                return kwargs["image_base64"], kwargs["mime_type"], "tp-1", True
            return _b64(f"translated-{cut_no}"), "image/png", f"tp-{cut_no}", False

        with (
            patch.object(
                ContiOrchestratorService,
                "translate_cut_text_only",
                new=AsyncMock(side_effect=_translate_side_effect),
            ),
            patch("app.domain.teaser_compat.router.save_export_artifacts", return_value="export_test"),
        ):
            response = test_client.post(
                "/api/teaser/translate",
                json={
                    "source_language": "ko",
                    "target_language": "ja",
                    "cuts": [
                        {
                            "index": i,
                            "image_base64": _b64(f"orig-{i}"),
                            "mime_type": "image/png",
                            "dialogue": [f"line {i}"],
                            "narration": f"narration {i}",
                            "description": f"cut {i}",
                        }
                        for i in range(1, 10)
                    ],
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["cuts"][0]["image_base64"] == _b64("orig-1")
        assert payload["cuts"][1]["image_base64"] == _b64("translated-2")


class TestExportArtifacts:
    def test_save_export_artifacts_writes_expected_files(self, tmp_path):
        with patch("app.domain.teaser_compat.export_artifacts._outputs_root", return_value=tmp_path):
            run_id = save_export_artifacts(
                request_payload={"source_text": "sample"},
                plan_payload={"title": "plan"},
                anchor_prompt="anchor prompt",
                anchor_image_base64=_b64("anchor image"),
                prompt_snapshots=[
                    PromptSnapshot(cut_number=1, raw_prompt="raw 1", styled_prompt="styled 1")
                ],
                original_images=[
                    ImageSnapshot(cut_number=1, image_base64=_b64("orig image"), mime_type="image/png")
                ],
                translated_language="en",
                translated_images=[
                    ImageSnapshot(cut_number=1, image_base64=_b64("translated image"), mime_type="image/png")
                ],
                translation_records=[{"cut_number": 1, "used_fallback_original": False}],
            )

        export_dir = tmp_path / run_id
        assert (export_dir / "request.json").exists()
        assert (export_dir / "plan.json").exists()
        assert (export_dir / "prompts" / "anchor_prompt.txt").exists()
        assert (export_dir / "prompts" / "cut_01.raw.txt").exists()
        assert (export_dir / "prompts" / "cut_01.styled.txt").exists()
        assert (export_dir / "images" / "original" / "anchor.png").exists()
        assert (export_dir / "images" / "original" / "cut_01.png").exists()
        assert (export_dir / "images" / "translated_en" / "cut_01.png").exists()
        assert (export_dir / "manifest.json").exists()
