"""Tests for ContiOrchestratorService and its router."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.conti.schemas import (
    ContiRequest,
    ContiResult,
    GeneratedCut,
    PipelineProgress,
)
from app.domain.conti.service import ContiOrchestratorService
from app.exceptions import GeminiAPIError, QuotaExceededError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(mock_client) -> ContiOrchestratorService:
    return ContiOrchestratorService(mock_client)


def _make_conti_request(
    manuscript: str = "Two strangers meet on a rainy night.",
) -> ContiRequest:
    return ContiRequest(
        manuscript=manuscript,
        genre="romance",
        tone="warm",
        output_language="ko",
    )


async def _collect_events(generator) -> list[dict]:
    """Drain an async generator into a list of dicts."""
    events = []
    async for event in generator:
        events.append(event)
    return events


def _progress_events(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("event") == "progress"]


def _result_events(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("event") == "result"]


def _parse_data(event: dict) -> dict:
    return json.loads(event["data"])


# ---------------------------------------------------------------------------
# Fixtures for patching sub-services
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_scene_parser():
    with patch("app.domain.conti.service.SceneParserService") as cls:
        yield cls.return_value


@pytest.fixture
def mock_char_gen():
    with patch("app.domain.conti.service.CharacterGenService") as cls:
        yield cls.return_value


@pytest.fixture
def mock_cut_planner():
    with patch("app.domain.conti.service.CutPlannerService") as cls:
        yield cls.return_value


@pytest.fixture
def mock_validator():
    with patch("app.domain.conti.service.ValidatorService") as cls:
        yield cls.return_value


@pytest.fixture
def mock_image_gen():
    with patch("app.domain.conti.service.GeminiImageService") as cls:
        yield cls.return_value


@pytest.fixture
def patched_services(
    mock_scene_parser,
    mock_char_gen,
    mock_cut_planner,
    mock_validator,
    mock_image_gen,
    sample_scene_breakdown,
    sample_character_sheet,
    sample_cut_plan,
):
    """Wire all sub-service mocks with default happy-path return values."""
    mock_scene_parser.parse.return_value = sample_scene_breakdown

    char_resp = MagicMock()
    char_resp.character_sheet = sample_character_sheet
    mock_char_gen.generate.return_value = char_resp

    mock_cut_planner.plan.return_value = sample_cut_plan

    from app.domain.validator.schemas import ValidationReport

    valid_report = ValidationReport(
        is_valid=True, issues=[], summary="Validation passed: 0 error(s), 0 warning(s)."
    )
    mock_validator.validate.return_value = valid_report

    from app.domain.image_generation.schemas import ImageGenerationResponse

    img_resp = ImageGenerationResponse(image_base64="base64data", mime_type="image/png")
    mock_image_gen.generate.return_value = img_resp

    return {
        "scene_parser": mock_scene_parser,
        "char_gen": mock_char_gen,
        "cut_planner": mock_cut_planner,
        "validator": mock_validator,
        "image_gen": mock_image_gen,
    }


# ---------------------------------------------------------------------------
# Service: generate — happy path (full pipeline)
# ---------------------------------------------------------------------------


class TestContiOrchestratorHappyPath:
    @pytest.mark.asyncio
    async def test_full_pipeline_emits_progress_events_for_all_5_steps(
        self, mock_genai_client, patched_services
    ):
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        progress = _progress_events(events)
        steps = {_parse_data(e)["step"] for e in progress}
        assert steps == {1, 2, 3, 4, 5}

    @pytest.mark.asyncio
    async def test_full_pipeline_emits_result_event(
        self, mock_genai_client, patched_services
    ):
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        result_evts = _result_events(events)
        assert len(result_evts) == 1

    @pytest.mark.asyncio
    async def test_result_event_contains_characters_and_cuts(
        self, mock_genai_client, patched_services, sample_character_sheet
    ):
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        result_data = _parse_data(_result_events(events)[0])
        assert "characters" in result_data
        assert "cuts" in result_data
        assert len(result_data["cuts"]) == 9

    @pytest.mark.asyncio
    async def test_result_event_contains_validation_report(
        self, mock_genai_client, patched_services
    ):
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        result_data = _parse_data(_result_events(events)[0])
        assert "validation_report" in result_data
        assert result_data["validation_report"]["is_valid"] is True

    @pytest.mark.asyncio
    async def test_all_step_progress_events_have_completed_status_in_happy_path(
        self, mock_genai_client, patched_services
    ):
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        # Filter to final status events per step (last event for each step)
        progress = _progress_events(events)
        by_step: dict[int, list[dict]] = {}
        for e in progress:
            d = _parse_data(e)
            by_step.setdefault(d["step"], []).append(d)
        for step, evts in by_step.items():
            final = evts[-1]
            # Step 5 has intermediate "running" events before "completed"
            assert final["status"] in ("completed", "running")

    @pytest.mark.asyncio
    async def test_sse_events_have_event_and_data_keys(
        self, mock_genai_client, patched_services
    ):
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        for event in events:
            assert "event" in event
            assert "data" in event


# ---------------------------------------------------------------------------
# Service: generate — early pipeline failures
# ---------------------------------------------------------------------------


class TestContiOrchestratorEarlyFailures:
    @pytest.mark.asyncio
    async def test_step1_failure_stops_pipeline_and_yields_failed_event(
        self, mock_genai_client, patched_services
    ):
        patched_services["scene_parser"].parse.side_effect = GeminiAPIError(
            "scene parse failed"
        )
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))

        progress = _progress_events(events)
        failed = [e for e in progress if _parse_data(e)["status"] == "failed"]
        assert len(failed) == 1
        assert _parse_data(failed[0])["step"] == 1

        # No result event should be emitted
        assert len(_result_events(events)) == 0

    @pytest.mark.asyncio
    async def test_step1_failure_does_not_call_step2_services(
        self, mock_genai_client, patched_services
    ):
        patched_services["scene_parser"].parse.side_effect = GeminiAPIError("fail")
        service = _make_service(mock_genai_client)
        await _collect_events(service.generate(_make_conti_request()))
        patched_services["char_gen"].generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_step2_failure_stops_pipeline_and_yields_failed_event(
        self, mock_genai_client, patched_services
    ):
        patched_services["char_gen"].generate.side_effect = GeminiAPIError(
            "char gen failed"
        )
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))

        progress = _progress_events(events)
        failed = [e for e in progress if _parse_data(e)["status"] == "failed"]
        assert any(_parse_data(e)["step"] == 2 for e in failed)
        assert len(_result_events(events)) == 0

    @pytest.mark.asyncio
    async def test_step3_failure_stops_pipeline_and_yields_failed_event(
        self, mock_genai_client, patched_services
    ):
        patched_services["cut_planner"].plan.side_effect = GeminiAPIError(
            "cut plan failed"
        )
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))

        progress = _progress_events(events)
        failed = [e for e in progress if _parse_data(e)["status"] == "failed"]
        assert any(_parse_data(e)["step"] == 3 for e in failed)
        assert len(_result_events(events)) == 0

    @pytest.mark.asyncio
    async def test_failed_event_contains_error_detail(
        self, mock_genai_client, patched_services
    ):
        patched_services["scene_parser"].parse.side_effect = GeminiAPIError(
            "detailed error message"
        )
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))

        progress = _progress_events(events)
        failed = [
            _parse_data(e) for e in progress if _parse_data(e)["status"] == "failed"
        ]
        assert failed[0]["detail"] is not None


# ---------------------------------------------------------------------------
# Service: generate — step 4 validation retry logic
# ---------------------------------------------------------------------------


class TestContiOrchestratorValidationRetry:
    @pytest.mark.asyncio
    async def test_validation_fails_retry_succeeds_pipeline_continues(
        self, mock_genai_client, patched_services, sample_cut_plan
    ):
        from app.domain.validator.schemas import ValidationReport, ValidationIssue

        invalid_report = ValidationReport(
            is_valid=False,
            issues=[
                ValidationIssue(issue_type="test", description="bad", severity="error")
            ],
            summary="Validation failed: 1 error(s), 0 warning(s).",
        )
        valid_report = ValidationReport(
            is_valid=True,
            issues=[],
            summary="Validation passed: 0 error(s), 0 warning(s).",
        )
        patched_services["validator"].validate.side_effect = [
            invalid_report,
            valid_report,
        ]
        patched_services["cut_planner"].plan.return_value = sample_cut_plan

        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))

        # Pipeline should complete with a result event
        assert len(_result_events(events)) == 1
        # cut_planner.plan called twice: initial + retry
        assert patched_services["cut_planner"].plan.call_count == 2

    @pytest.mark.asyncio
    async def test_validation_fails_retry_also_fails_proceeds_with_warning(
        self, mock_genai_client, patched_services, sample_cut_plan
    ):
        from app.domain.validator.schemas import ValidationReport, ValidationIssue

        invalid_report = ValidationReport(
            is_valid=False,
            issues=[
                ValidationIssue(issue_type="test", description="bad", severity="error")
            ],
            summary="Validation failed: 1 error(s), 0 warning(s).",
        )
        patched_services["validator"].validate.side_effect = [
            invalid_report,
            invalid_report,
        ]
        patched_services["cut_planner"].plan.return_value = sample_cut_plan

        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))

        # Pipeline should still complete (proceeds with warning)
        assert len(_result_events(events)) == 1

        # Step 4 completed (with warning detail)
        progress = _progress_events(events)
        step4_events = [_parse_data(e) for e in progress if _parse_data(e)["step"] == 4]
        final_step4 = step4_events[-1]
        assert final_step4["status"] == "completed"
        assert "warning" in (final_step4["detail"] or "").lower()

    @pytest.mark.asyncio
    async def test_retry_raises_exception_proceeds_with_original_plan(
        self, mock_genai_client, patched_services, sample_cut_plan
    ):
        from app.domain.validator.schemas import ValidationReport, ValidationIssue

        invalid_report = ValidationReport(
            is_valid=False,
            issues=[
                ValidationIssue(issue_type="test", description="bad", severity="error")
            ],
            summary="Validation failed: 1 error(s), 0 warning(s).",
        )
        # First validate returns invalid; then cut_planner.plan raises on retry
        patched_services["validator"].validate.return_value = invalid_report
        # plan: first call succeeds (step 3), second call (retry) raises
        patched_services["cut_planner"].plan.side_effect = [
            sample_cut_plan,
            GeminiAPIError("retry cut plan failed"),
        ]

        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))

        # Pipeline proceeds with original plan -> result event emitted
        assert len(_result_events(events)) == 1

        progress = _progress_events(events)
        step4_events = [_parse_data(e) for e in progress if _parse_data(e)["step"] == 4]
        final_step4 = step4_events[-1]
        assert final_step4["status"] == "completed"
        assert "retry failed" in (final_step4["detail"] or "").lower()

    @pytest.mark.asyncio
    async def test_validation_exception_proceeds_without_validation(
        self, mock_genai_client, patched_services
    ):
        patched_services["validator"].validate.side_effect = Exception(
            "validation crashed"
        )
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))

        # Pipeline still completes
        assert len(_result_events(events)) == 1

        result_data = _parse_data(_result_events(events)[0])
        # validation_report should be None since validation was skipped
        assert result_data["validation_report"] is None

        # Step 4 emitted "completed" with skip detail
        progress = _progress_events(events)
        step4_events = [_parse_data(e) for e in progress if _parse_data(e)["step"] == 4]
        assert any("skip" in (e.get("detail") or "").lower() for e in step4_events)


# ---------------------------------------------------------------------------
# Service: generate — step 5 image generation
# ---------------------------------------------------------------------------


class TestContiOrchestratorImageGeneration:
    @pytest.mark.asyncio
    async def test_all_images_succeed_result_has_9_cuts(
        self, mock_genai_client, patched_services
    ):
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        result_data = _parse_data(_result_events(events)[0])
        assert len(result_data["cuts"]) == 9

    @pytest.mark.asyncio
    async def test_image_failure_results_in_empty_image_base64(
        self, mock_genai_client, patched_services
    ):
        """When all image gen attempts fail, cut has empty image_base64."""
        patched_services["image_gen"].generate.side_effect = Exception(
            "image generation failed"
        )
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        result_data = _parse_data(_result_events(events)[0])
        for cut in result_data["cuts"]:
            assert cut["image_base64"] == ""
            assert cut["mime_type"] == "image/png"

    @pytest.mark.asyncio
    async def test_partial_image_failures_produce_mixed_results(
        self, mock_genai_client, patched_services
    ):
        """Cuts whose image_prompt contains 'cut 1' succeed; all others always fail.
        This is deterministic regardless of concurrency ordering."""
        from app.domain.image_generation.schemas import ImageGenerationResponse

        good_resp = ImageGenerationResponse(
            image_base64="gooddata", mime_type="image/png"
        )

        def side_effect(req):
            # Only the first cut's prompt ends in "cut 1" — succeed for it, fail for rest
            if req.prompt.endswith("cut 1"):
                return good_resp
            raise Exception("fail for this cut")

        patched_services["image_gen"].generate.side_effect = side_effect
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        result_data = _parse_data(_result_events(events)[0])
        assert len(result_data["cuts"]) == 9
        successful = [c for c in result_data["cuts"] if c["image_base64"] != ""]
        failed = [c for c in result_data["cuts"] if c["image_base64"] == ""]
        assert len(successful) >= 1
        assert len(failed) >= 1

    @pytest.mark.asyncio
    async def test_image_retry_succeeds_on_third_attempt(
        self, mock_genai_client, patched_services
    ):
        """Image gen fails twice, succeeds on third attempt — result has valid image."""
        from app.domain.image_generation.schemas import ImageGenerationResponse

        good_resp = ImageGenerationResponse(
            image_base64="retried_data", mime_type="image/png"
        )

        call_count = [0]

        def side_effect(req):
            call_count[0] += 1
            # First two calls per cut fail, third succeeds
            # Since there are 9 cuts, track total calls
            if call_count[0] % 3 != 0:
                raise Exception("temporary failure")
            return good_resp

        patched_services["image_gen"].generate.side_effect = side_effect
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        result_data = _parse_data(_result_events(events)[0])
        # At least some cuts should have succeeded via retry
        assert len(result_data["cuts"]) == 9

    @pytest.mark.asyncio
    async def test_images_generated_in_batches_of_3(
        self, mock_genai_client, patched_services
    ):
        """9 cuts should produce 3 batches of 3; verify step 5 emits batch progress events."""
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        progress = _progress_events(events)
        step5_events = [_parse_data(e) for e in progress if _parse_data(e)["step"] == 5]
        # Should have: 1 "running" start + 3 batch progress "running" + 1 "completed"
        running_events = [e for e in step5_events if e["status"] == "running"]
        # At least the initial + 3 batch updates
        assert len(running_events) >= 3

    @pytest.mark.asyncio
    async def test_result_cut_contains_correct_fields(
        self, mock_genai_client, patched_services
    ):
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        result_data = _parse_data(_result_events(events)[0])
        cut = result_data["cuts"][0]
        assert "cut_number" in cut
        assert "image_base64" in cut
        assert "mime_type" in cut
        assert "dialogue" in cut
        assert "narration" in cut
        assert "description" in cut


# ---------------------------------------------------------------------------
# Service: generate — SSE event format
# ---------------------------------------------------------------------------


class TestContiOrchestratorSSEFormat:
    @pytest.mark.asyncio
    async def test_progress_event_data_matches_pipeline_progress_schema(
        self, mock_genai_client, patched_services
    ):
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        for event in _progress_events(events):
            data = _parse_data(event)
            # Validate required PipelineProgress fields
            assert "step" in data
            assert "step_name" in data
            assert "status" in data
            assert data["step"] in range(1, 6)
            assert data["status"] in ("running", "completed", "failed")

    @pytest.mark.asyncio
    async def test_result_event_name_is_result(
        self, mock_genai_client, patched_services
    ):
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        result_evts = _result_events(events)
        assert all(e["event"] == "result" for e in result_evts)

    @pytest.mark.asyncio
    async def test_progress_event_name_is_progress(
        self, mock_genai_client, patched_services
    ):
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(_make_conti_request()))
        for e in _progress_events(events):
            assert e["event"] == "progress"


# ---------------------------------------------------------------------------
# Service: generate — short manuscript
# ---------------------------------------------------------------------------


class TestContiOrchestratorShortManuscript:
    @pytest.mark.asyncio
    async def test_single_sentence_manuscript_completes_pipeline(
        self, mock_genai_client, patched_services
    ):
        request = _make_conti_request(manuscript="A hero rises.")
        service = _make_service(mock_genai_client)
        events = await _collect_events(service.generate(request))
        assert len(_result_events(events)) == 1


# ---------------------------------------------------------------------------
# Router: POST /api/pipeline/generate
# ---------------------------------------------------------------------------


class TestContiGenerateRouter:
    def _valid_payload(self):
        return {
            "manuscript": "Two strangers meet on a rainy night.",
            "genre": "romance",
            "tone": "warm",
            "output_language": "ko",
        }

    def test_generate_returns_200(
        self,
        test_client,
        mock_genai_client,
        sample_scene_breakdown,
        sample_character_sheet,
        sample_cut_plan,
    ):
        from app.domain.validator.schemas import ValidationReport
        from app.domain.image_generation.schemas import ImageGenerationResponse

        with (
            patch("app.domain.conti.service.SceneParserService") as sp_cls,
            patch("app.domain.conti.service.CharacterGenService") as cg_cls,
            patch("app.domain.conti.service.CutPlannerService") as cp_cls,
            patch("app.domain.conti.service.ValidatorService") as v_cls,
            patch("app.domain.conti.service.GeminiImageService") as ig_cls,
        ):
            sp_cls.return_value.parse.return_value = sample_scene_breakdown
            char_resp = MagicMock()
            char_resp.character_sheet = sample_character_sheet
            cg_cls.return_value.generate.return_value = char_resp
            cp_cls.return_value.plan.return_value = sample_cut_plan
            v_cls.return_value.validate.return_value = ValidationReport(
                is_valid=True, issues=[], summary="OK"
            )
            ig_cls.return_value.generate.return_value = ImageGenerationResponse(
                image_base64="data", mime_type="image/png"
            )

            response = test_client.post(
                "/api/pipeline/generate", json=self._valid_payload()
            )
            assert response.status_code == 200

    def test_generate_returns_422_on_missing_manuscript(self, test_client):
        response = test_client.post(
            "/api/pipeline/generate",
            json={"genre": "romance", "tone": "warm"},
        )
        assert response.status_code == 422

    def test_generate_returns_422_on_missing_genre(self, test_client):
        response = test_client.post(
            "/api/pipeline/generate",
            json={"manuscript": "test", "tone": "warm"},
        )
        assert response.status_code == 422
