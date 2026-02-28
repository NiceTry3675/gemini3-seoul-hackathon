"""Shared pytest fixtures for the backend test suite.

GOOGLE_API_KEY must be set before any app module is imported because
app/config.py instantiates Settings() at module level.  We patch the
environment variable here using pytest's autouse session fixture so it
is visible to every test file regardless of import order.
"""
from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Ensure GOOGLE_API_KEY is present before any app import resolves Settings()
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Called very early by pytest, before any collection or import."""
    os.environ.setdefault("GOOGLE_API_KEY", "test-key")


# ---------------------------------------------------------------------------
# Mock genai.Client fixture
# ---------------------------------------------------------------------------

def _default_response() -> MagicMock:
    response = MagicMock()
    response.text = "Hello, world!"
    response.usage_metadata = MagicMock(
        prompt_token_count=10,
        candidates_token_count=5,
        total_token_count=15,
    )
    response.candidates = []
    return response


@pytest.fixture
def mock_genai_client():
    """Return a MagicMock that mimics google.genai.Client with async support.

    Services use ``client.aio.models.generate_content`` (async).
    Router/integration tests may still reference ``client.models.*`` via MagicMock fallback.
    """
    client = MagicMock()
    default_resp = _default_response()

    # Sync fallback (legacy tests / MagicMock auto-attr)
    client.models.generate_content.return_value = default_resp

    # Async path used by all services
    client.aio.models.generate_content = AsyncMock(return_value=default_resp)
    client.aio.models.generate_videos = AsyncMock()
    client.aio.operations.get = AsyncMock()

    return client


# ---------------------------------------------------------------------------
# TestClient fixture that overrides the genai client dependency
# ---------------------------------------------------------------------------

@pytest.fixture
def test_client(mock_genai_client):
    """FastAPI TestClient with get_genai_client dependency overridden."""
    from app.main import app
    from app.shared.client import get_genai_client

    app.dependency_overrides[get_genai_client] = lambda: mock_genai_client
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Shared domain fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_novel_input():
    """A minimal valid NovelInput."""
    from app.domain.scene_parser.schemas import NovelInput
    return NovelInput(
        manuscript="Two strangers meet on a rainy night and fall in love.",
        genre="romance",
        tone="warm",
        output_language="ko",
    )


@pytest.fixture
def sample_scene_breakdown():
    """A valid SceneBreakdown with 2 scenes."""
    from app.domain.scene_parser.schemas import Scene, SceneBreakdown
    return SceneBreakdown(
        scenes=[
            Scene(
                scene_number=1,
                title="Rainy Meeting",
                summary="Two strangers meet at a bus stop.",
                characters=["Alice", "Bob"],
                mood="bittersweet",
                key_dialogue=["Do you have an umbrella?"],
            ),
            Scene(
                scene_number=2,
                title="First Date",
                summary="They share coffee and stories.",
                characters=["Alice", "Bob"],
                mood="warm",
                key_dialogue=["I've never met anyone like you."],
            ),
        ]
    )


@pytest.fixture
def sample_character_sheet():
    """A valid CharacterSheet with 2 characters."""
    from app.domain.character_gen.schemas import Character, CharacterSheet
    return CharacterSheet(
        characters=[
            Character(
                name="Alice",
                appearance="Tall woman with brown hair and green eyes",
                personality="Warm and curious",
                role="protagonist",
                visual_prompt="tall woman, brown hair, green eyes, warm smile, realistic",
            ),
            Character(
                name="Bob",
                appearance="Medium-height man with dark hair",
                personality="Quiet and thoughtful",
                role="love interest",
                visual_prompt="medium height man, dark hair, thoughtful expression, realistic",
            ),
        ]
    )


@pytest.fixture
def sample_cut_plan():
    """A valid CutPlan with exactly 9 cuts."""
    from app.domain.cut_planner.schemas import Cut, CutPlan
    cuts = [
        Cut(
            cut_number=i,
            scene_ref=1 if i <= 5 else 2,
            description=f"Cut {i} description",
            dialogue=[f"Dialogue for cut {i}"],
            narration=f"Narration for cut {i}",
            camera_angle="wide shot",
            emotion="neutral",
            image_prompt=f"image prompt for cut {i}",
        )
        for i in range(1, 10)
    ]
    return CutPlan(cuts=cuts)


# ---------------------------------------------------------------------------
# Helper to create a structured mock response
# ---------------------------------------------------------------------------

def mock_structured_response(text: str) -> MagicMock:
    """Create a MagicMock response with the given JSON text."""
    response = MagicMock()
    response.text = text
    response.usage_metadata = None
    response.candidates = []
    return response
