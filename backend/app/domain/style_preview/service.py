from __future__ import annotations

import base64
import io
import logging
import sys
import os

from PIL import Image

# teaser_pipeline lives in backend/, not in backend/app/.
# Resolve the backend root and add it to sys.path if needed.
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from dotenv import find_dotenv, load_dotenv
from google import genai
from google.genai import types

from teaser_pipeline import (
    _first_image_from_response,
    _image_to_png_bytes,
)
from teaser_prompts import style_prompt

load_dotenv(find_dotenv())
logger = logging.getLogger(__name__)


def generate_style_preview(style_template: str, story_text: str | None = None) -> list[str]:
    """Generate a 1x4 grid image for the given style_template and split it into 4 base64 PNG strings."""
    try:
        style_descriptor = style_prompt(style_template)
    except ValueError:
        return []

    prompt_text = (
        f"{style_descriptor}\n\n"
        "Generate a horizontal panoramic image showing exactly 4 distinct sample scenes "
        "placed side by side from left to right, like a comic strip. "
        "Scene 1: a character portrait. Scene 2: an action scene. "
        "Scene 3: a landscape. Scene 4: an emotional close-up. "
        "Each scene occupies exactly 1/4 of the width. "
        "Thin white vertical lines separate the scenes. No text, no watermark."
    )

    try:
        client = genai.Client()
        resp = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[prompt_text],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="16:9"),
            ),
        )
        image = _first_image_from_response(resp)
        png_bytes = _image_to_png_bytes(image)
    except Exception as exc:
        logger.exception("Gemini image generation failed for style %s: %s", style_template, exc)
        return []

    try:
        pil_img = Image.open(io.BytesIO(png_bytes))
        w, h = pil_img.size
        piece_w = w // 4
        images_b64: list[str] = []
        for i in range(4):
            piece = pil_img.crop((i * piece_w, 0, (i + 1) * piece_w, h))
            buf = io.BytesIO()
            piece.save(buf, format="PNG")
            images_b64.append(base64.b64encode(buf.getvalue()).decode("ascii"))
        return images_b64
    except Exception as exc:
        logger.exception("Image splitting failed: %s", exc)
        return []
