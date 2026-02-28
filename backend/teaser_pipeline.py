from __future__ import annotations

import base64
import io
import json
import os
from typing import Iterable

from dotenv import find_dotenv, load_dotenv
from google import genai
from google.genai import types
from PIL import Image
from pydantic import ValidationError

from .teaser_models import TeaserCut, TeaserPlan, TeaserRequest, TeaserResult
from .teaser_prompts import (
    STORYBOARD_SYSTEM,
    build_anchor_image_prompt,
    build_panel_image_prompt,
    build_storyboard_user_prompt,
)


def _ensure_api_key() -> None:
    load_dotenv(find_dotenv())
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return
    raise RuntimeError("Missing API key. Set GOOGLE_API_KEY or GEMINI_API_KEY (e.g. via .env).")


def make_client() -> genai.Client:
    _ensure_api_key()
    return genai.Client()


def _extract_json_text(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        raise ValueError("Empty model response")

    # Common case: model wraps JSON in ```json fences.
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()

    # Fast path.
    try:
        json.loads(s)
        return s
    except Exception:
        pass

    # Fallback: take the first {...} block.
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not locate JSON object in model response")
    candidate = s[start : end + 1]
    json.loads(candidate)
    return candidate


def generate_plan(client: genai.Client, req: TeaserRequest, *, max_attempts: int = 2) -> TeaserPlan:
    user_prompt = build_storyboard_user_prompt(req)

    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        system_prompt = STORYBOARD_SYSTEM
        if attempt > 1:
            system_prompt = system_prompt + "\n\nOutput ONLY valid JSON."

        resp = client.models.generate_content(
            model=req.text_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            ),
        )

        try:
            plan_json = _extract_json_text(resp.text or "")
            plan = TeaserPlan.model_validate_json(plan_json)
            # Enforce requested values (the model sometimes mirrors but can drift).
            plan = plan.model_copy(
                update={"output_language": req.output_language, "style_template": req.style_template}
            )
            return plan
        except (ValueError, ValidationError, json.JSONDecodeError) as exc:
            last_err = exc

    raise RuntimeError(f"Failed to generate valid plan JSON after {max_attempts} attempts: {last_err}")


def _first_image_from_response(resp: types.GenerateContentResponse) -> Image.Image:
    # Try convenience path first.
    parts = getattr(resp, "parts", None)
    if parts:
        for part in parts:
            if getattr(part, "inline_data", None) is not None:
                return part.as_image()

    # Fallback: traverse candidates.
    for cand in getattr(resp, "candidates", []) or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            if getattr(part, "inline_data", None) is not None:
                return part.as_image()

    raise RuntimeError("Image model response contained no image parts")


def _image_to_base64_png(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _generate_image(
    client: genai.Client,
    *,
    model: str,
    prompt: str,
    references: Iterable[Image.Image],
    max_attempts: int = 2,
) -> Image.Image:
    contents: list[object] = [prompt]
    for ref in references:
        contents.append(ref)

    last_err: Exception | None = None
    for _ in range(max_attempts):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="1:1"),
                ),
            )
            return _first_image_from_response(resp)
        except Exception as exc:
            last_err = exc

    raise RuntimeError(f"Image generation failed after {max_attempts} attempts: {last_err}")


def run_teaser(client: genai.Client, req: TeaserRequest) -> TeaserResult:
    plan = generate_plan(client, req)

    # 1) Character anchor image
    anchor_prompt = build_anchor_image_prompt(plan)
    anchor_img = _generate_image(
        client,
        model=req.image_model,
        prompt=anchor_prompt,
        references=[],
    )
    anchor_b64 = _image_to_base64_png(anchor_img)

    # 2) Panels: sequential with references.
    cuts: list[TeaserCut] = []
    prev_img: Image.Image | None = None
    for panel in sorted(plan.panels, key=lambda p: p.index):
        panel_prompt = build_panel_image_prompt(plan, panel)

        if panel.index == 1:
            refs = [anchor_img]
        else:
            # MVP rule: anchor + previous panel for cuts 2..9.
            refs = [anchor_img, prev_img] if prev_img is not None else [anchor_img]

        img = _generate_image(
            client,
            model=req.image_model,
            prompt=panel_prompt,
            references=[r for r in refs if r is not None],
        )
        prev_img = img
        cuts.append(TeaserCut(index=panel.index, image_base64=_image_to_base64_png(img)))

    return TeaserResult(plan=plan, character_anchor_image_base64=anchor_b64, cuts=cuts)
