from __future__ import annotations

import json


def extract_json_text(raw: str) -> str:
    """Extract a JSON object from a model response that may include markdown fences."""
    s = (raw or "").strip()
    if not s:
        raise ValueError("Empty model response")

    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()

    try:
        json.loads(s)
        return s
    except Exception:
        pass

    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not locate JSON object in model response")
    candidate = s[start : end + 1]
    json.loads(candidate)
    return candidate
