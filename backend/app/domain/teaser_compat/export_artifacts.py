from __future__ import annotations

import base64
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from PIL import Image


@dataclass(frozen=True)
class PromptSnapshot:
    cut_number: int
    raw_prompt: str
    styled_prompt: str


@dataclass(frozen=True)
class ImageSnapshot:
    cut_number: int
    image_base64: str
    mime_type: str = "image/png"


def _outputs_root() -> Path:
    return Path(__file__).resolve().parents[4] / "outputs"


def _create_export_dir() -> tuple[str, Path]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"export_{ts}_{uuid4().hex[:8]}"
    out_dir = _outputs_root() / run_id
    out_dir.mkdir(parents=True, exist_ok=False)
    return run_id, out_dir


def _decode_image_to_png_bytes(image_base64: str, mime_type: str) -> bytes:
    if not image_base64:
        return b""

    raw = base64.b64decode(image_base64)
    if not raw:
        return b""

    if mime_type == "image/png":
        return raw

    try:
        with Image.open(io.BytesIO(raw)) as img:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        return raw


def _write_prompt_files(base_dir: Path, prompt_snapshots: list[PromptSnapshot]) -> None:
    prompt_dir = base_dir / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)

    for item in sorted(prompt_snapshots, key=lambda p: p.cut_number):
        stem = f"cut_{item.cut_number:02d}"
        (prompt_dir / f"{stem}.raw.txt").write_text(item.raw_prompt, encoding="utf-8")
        (prompt_dir / f"{stem}.styled.txt").write_text(item.styled_prompt, encoding="utf-8")


def _write_images(base_dir: Path, images: list[ImageSnapshot]) -> list[str]:
    base_dir.mkdir(parents=True, exist_ok=True)
    written_files: list[str] = []
    for item in sorted(images, key=lambda c: c.cut_number):
        png_bytes = _decode_image_to_png_bytes(item.image_base64, item.mime_type)
        filename = f"cut_{item.cut_number:02d}.png"
        (base_dir / filename).write_bytes(png_bytes)
        written_files.append(filename)
    return written_files


def save_export_artifacts(
    *,
    request_payload: dict,
    plan_payload: dict,
    anchor_prompt: str,
    anchor_image_base64: str,
    prompt_snapshots: list[PromptSnapshot],
    original_images: list[ImageSnapshot],
    translated_language: str | None = None,
    translated_images: list[ImageSnapshot] | None = None,
    translation_records: list[dict] | None = None,
) -> str:
    run_id, out_dir = _create_export_dir()

    (out_dir / "request.json").write_text(
        json.dumps(request_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "plan.json").write_text(
        json.dumps(plan_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    prompt_dir = out_dir / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    (prompt_dir / "anchor_prompt.txt").write_text(anchor_prompt or "", encoding="utf-8")
    _write_prompt_files(out_dir, prompt_snapshots)

    image_dir = out_dir / "images"
    original_dir = image_dir / "original"
    original_files = _write_images(original_dir, original_images)

    anchor_file = ""
    if anchor_image_base64:
        anchor_file = "anchor.png"
        (original_dir / anchor_file).write_bytes(
            _decode_image_to_png_bytes(anchor_image_base64, "image/png")
        )

    translated_files: list[str] = []
    if translated_language and translated_images:
        translated_dir = image_dir / f"translated_{translated_language}"
        translated_files = _write_images(translated_dir, translated_images)

    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "translated_to_language": translated_language,
        "files": {
            "anchor": f"images/original/{anchor_file}" if anchor_file else None,
            "original_cuts": [f"images/original/{name}" for name in original_files],
            "translated_cuts": [
                f"images/translated_{translated_language}/{name}" for name in translated_files
            ] if translated_language else [],
        },
        "translation": {
            "enabled": bool(translated_language),
            "records": translation_records or [],
        },
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return run_id
