from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a literary analyst. Given a manuscript excerpt, identify its genre and tone.\n"
    "Respond ONLY with a JSON object like: {\"genre\": \"...\", \"tone\": \"...\"}\n"
    "genre: the primary literary genre (e.g. fantasy, romance, thriller, sci-fi, horror, mystery, drama, comedy, historical)\n"
    "tone: the dominant emotional tone (e.g. dark, humorous, melancholic, hopeful, tense, mysterious, whimsical, epic, lyrical)\n"
    "Use a single word or short phrase for each. Do not include any other text."
)


async def extract_genre_tone(client: genai.Client, manuscript: str) -> dict[str, str]:
    """Extract genre and tone from a manuscript using Gemini."""
    preview = manuscript[:3000]

    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_PROMPT,
        response_mime_type="application/json",
    )

    response = await client.aio.models.generate_content(
        model=settings.TEXT_MODEL,
        contents=f"Analyze this manuscript:\n\n{preview}",
        config=config,
    )

    text = (response.text or "{}").strip()
    if text.startswith("```json"):
        text = text.removeprefix("```json").removesuffix("```").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").removesuffix("```").strip()

    data = json.loads(text)
    genre = data.get("genre", "general")
    tone = data.get("tone", "neutral")

    logger.info("Auto-extracted genre=%s, tone=%s", genre, tone)
    return {"genre": genre, "tone": tone}
