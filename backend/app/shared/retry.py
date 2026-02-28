from __future__ import annotations

import asyncio

from google import genai
from google.genai import types


def is_transient_network_error(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    hints = (
        "handshake operation timed out",
        "timed out",
        "ssl",
        "tls",
        "connection reset",
        "temporarily unavailable",
    )
    return any(h in text for h in hints)


async def generate_content_with_retries(
    client: genai.Client,
    *,
    model: str,
    contents: object,
    config: types.GenerateContentConfig,
    max_attempts: int = 3,
) -> types.GenerateContentResponse:
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await client.aio.models.generate_content(
                model=model, contents=contents, config=config,
            )
        except Exception as exc:
            last_err = exc
            if attempt >= max_attempts or not is_transient_network_error(exc):
                break
            await asyncio.sleep(min(2 ** (attempt - 1), 4))
    raise RuntimeError(f"Gemini request failed after {max_attempts} attempts: {last_err}")
