from __future__ import annotations

import json
from typing import Any

from google.genai import types
from pydantic import BaseModel


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_text(response: types.GenerateContentResponse) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    for cand in getattr(response, "candidates", []) or []:
        content = getattr(cand, "content", None)
        if content is None:
            continue
        for part in getattr(content, "parts", []) or []:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                return part_text
    return ""


def _loads_with_brace_fallback(text: str) -> Any:
    stripped = _strip_code_fences(text)
    if not stripped:
        raise ValueError("Empty structured response text")

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    for left, right in (("{", "}"), ("[", "]")):
        start = stripped.find(left)
        end = stripped.rfind(right)
        if start == -1 or end == -1 or end <= start:
            continue
        candidate = stripped[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError("Could not extract valid JSON from model response")


def extract_structured_data(response: types.GenerateContentResponse) -> Any:
    parsed = getattr(response, "parsed", None)
    if parsed is not None:
        if isinstance(parsed, BaseModel):
            return parsed.model_dump()
        if isinstance(parsed, (dict, list)):
            return parsed
        if isinstance(parsed, str):
            return _loads_with_brace_fallback(parsed)
        if isinstance(parsed, (int, float, bool)):
            return parsed

    return _loads_with_brace_fallback(_extract_text(response))
