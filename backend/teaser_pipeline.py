from __future__ import annotations

import base64
import io
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from dotenv import find_dotenv, load_dotenv
from google import genai
from google.genai import types
from PIL import Image
from pydantic import ValidationError

from app.config import settings
from teaser_models import (
    PromptPreviewCut,
    PromptPreviewResult,
    TeaserCut,
    TeaserPlan,
    TeaserRequest,
    TeaserResult,
)
from teaser_prompts import (
    build_anchor_image_prompt,
    build_grid_image_prompt,
    build_panel_image_prompt,
    build_storyboard_user_prompt,
    get_storyboard_retry_suffix,
    get_storyboard_system_prompt,
)


def _ensure_api_key() -> None:
    load_dotenv(find_dotenv())
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return
    raise RuntimeError("Missing API key. Set GOOGLE_API_KEY or GEMINI_API_KEY (e.g. via .env).")


def make_client() -> genai.Client:
    _ensure_api_key()
    # Use the configured request timeout for long preview generation calls.
    http_options = types.HttpOptions(timeout=settings.GENAI_REQUEST_TIMEOUT_SECONDS)
    return genai.Client(
        http_options=http_options,
    )


def _is_transient_network_error(exc: Exception) -> bool:
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


def _generate_content_with_retries(
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
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as exc:
            last_err = exc
            if attempt >= max_attempts or not _is_transient_network_error(exc):
                break
            time.sleep(min(2**(attempt - 1), 4))
    raise RuntimeError(f"Gemini request failed after {max_attempts} attempts: {last_err}")


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
        system_prompt = get_storyboard_system_prompt()
        if attempt > 1:
            system_prompt = system_prompt + "\n\n" + get_storyboard_retry_suffix()

        resp = _generate_content_with_retries(
            client,
            model=req.text_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            ),
            max_attempts=3,
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


@dataclass
class GeneratedImage:
    data: bytes
    mime_type: str
    ref_part: types.Part


def _blob_data_to_bytes(blob_data: object) -> bytes:
    if isinstance(blob_data, bytes):
        return blob_data
    if isinstance(blob_data, str):
        # Some SDK paths expose base64 string; decode defensively.
        return base64.b64decode(blob_data)
    raise RuntimeError(f"Unsupported inline_data.data type: {type(blob_data)!r}")


def _part_to_generated_image(part: object) -> GeneratedImage:
    inline = getattr(part, "inline_data", None)
    if inline is None:
        raise RuntimeError("Part has no inline_data")

    data = _blob_data_to_bytes(getattr(inline, "data", b""))
    if not data:
        raise RuntimeError("inline_data was empty")
    mime_type = getattr(inline, "mime_type", None) or "image/png"
    return GeneratedImage(
        data=data,
        mime_type=mime_type,
        ref_part=types.Part.from_bytes(data=data, mime_type=mime_type),
    )


def _first_image_from_response(resp: types.GenerateContentResponse) -> GeneratedImage:
    # Try convenience path first.
    parts = getattr(resp, "parts", None)
    if parts:
        for part in parts:
            if getattr(part, "inline_data", None) is not None:
                return _part_to_generated_image(part)

    # Fallback: traverse candidates.
    for cand in getattr(resp, "candidates", []) or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            if getattr(part, "inline_data", None) is not None:
                return _part_to_generated_image(part)

    raise RuntimeError("Image model response contained no image parts")


def _image_to_base64(image: GeneratedImage) -> str:
    return base64.b64encode(_image_to_png_bytes(image)).decode("ascii")


def _image_to_png_bytes(image: GeneratedImage) -> bytes:
    # Keep API output stable as PNG base64 for UI consumers.
    if image.mime_type == "image/png":
        return image.data

    try:
        pil = Image.open(io.BytesIO(image.data))
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        # Fallback to raw bytes when conversion fails (may not be PNG).
        return image.data


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _create_output_dir() -> Path:
    base = _project_root() / "outputs"
    run_id = f"teaser_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    out = base / run_id
    out.mkdir(parents=True, exist_ok=False)
    return out


def _generate_image(
    client: genai.Client,
    *,
    model: str,
    prompt: str,
    references: Iterable[types.Part],
    max_attempts: int = 2,
) -> GeneratedImage:
    contents: list[object] = [prompt]
    for ref in references:
        contents.append(ref)

    last_err: Exception | None = None
    for _ in range(max_attempts):
        try:
            resp = _generate_content_with_retries(
                client,
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="1:1"),
                ),
                max_attempts=3,
            )
            return _first_image_from_response(resp)
        except Exception as exc:
            last_err = exc

    raise RuntimeError(f"Image generation failed after {max_attempts} attempts: {last_err}")


def _split_grid_image(png_bytes: bytes, rows: int = 3, cols: int = 3) -> list[bytes]:
    """Split a grid image into individual cell PNGs (left-to-right, top-to-bottom)."""
    pil_img = Image.open(io.BytesIO(png_bytes))
    w, h = pil_img.size
    cell_w = w // cols
    cell_h = h // rows
    cells: list[bytes] = []
    for r in range(rows):
        for c in range(cols):
            cell = pil_img.crop((c * cell_w, r * cell_h, (c + 1) * cell_w, (r + 1) * cell_h))
            buf = io.BytesIO()
            cell.save(buf, format="PNG")
            cells.append(buf.getvalue())
    return cells


def run_teaser(client: genai.Client, req: TeaserRequest) -> TeaserResult:
    plan = generate_plan(client, req)
    output_dir = _create_output_dir()
    (output_dir / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    # 1) Character anchor image
    anchor_prompt = build_anchor_image_prompt(plan)
    (output_dir / "anchor_prompt.txt").write_text(anchor_prompt, encoding="utf-8")
    anchor_img = _generate_image(
        client,
        model=req.image_model,
        prompt=anchor_prompt,
        references=[],
    )
    anchor_png = _image_to_png_bytes(anchor_img)
    (output_dir / "anchor.png").write_bytes(anchor_png)
    anchor_b64 = base64.b64encode(anchor_png).decode("ascii")

    # 2) Generate all 9 panels as a single 3x3 grid image, then split.
    grid_prompt = build_grid_image_prompt(plan)
    (output_dir / "grid_prompt.txt").write_text(grid_prompt, encoding="utf-8")

    grid_img = _generate_image(
        client,
        model=req.image_model,
        prompt=grid_prompt,
        references=[anchor_img.ref_part],
    )
    grid_png = _image_to_png_bytes(grid_img)
    (output_dir / "grid.png").write_bytes(grid_png)

    cell_pngs = _split_grid_image(grid_png, rows=3, cols=3)

    cuts: list[TeaserCut] = []
    target_count = min(req.max_image_cuts, len(cell_pngs))
    for i in range(target_count):
        panel_index = i + 1
        (output_dir / f"cut_{panel_index:02d}.png").write_bytes(cell_pngs[i])
        cuts.append(TeaserCut(
            index=panel_index,
            image_base64=base64.b64encode(cell_pngs[i]).decode("ascii"),
        ))

    return TeaserResult(plan=plan, character_anchor_image_base64=anchor_b64, cuts=cuts)


def run_prompt_preview(client: genai.Client, req: TeaserRequest) -> PromptPreviewResult:
    plan = generate_plan(client, req)
    anchor_prompt = build_anchor_image_prompt(plan)

    cuts: list[PromptPreviewCut] = []
    for panel in sorted(plan.panels, key=lambda p: p.index):
        panel_prompt = build_panel_image_prompt(plan, panel)
        if panel.index == 1:
            refs = ["character_anchor"]
        else:
            refs = ["character_anchor", "previous_cut_image"]
        cuts.append(PromptPreviewCut(index=panel.index, prompt=panel_prompt, reference_inputs=refs))

    return PromptPreviewResult(plan=plan, anchor_prompt=anchor_prompt, cuts=cuts)
