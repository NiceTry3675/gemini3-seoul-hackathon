from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import tomllib

from teaser_models import Panel, TeaserPlan, TeaserRequest

_CONFIG_PATH = Path(__file__).with_name("system_instruction.toml")


@lru_cache(maxsize=1)
def _load_config() -> dict[str, object]:
    if not _CONFIG_PATH.exists():
        raise RuntimeError(f"Prompt config file not found: {_CONFIG_PATH}")
    with _CONFIG_PATH.open("rb") as f:
        data = tomllib.load(f)
    if not isinstance(data, dict):
        raise RuntimeError("Prompt config must be a TOML table")
    return data


def _require_str(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Invalid or missing prompt field: {field}")
    return value


def _prompt_value(name: str) -> str:
    cfg = _load_config()
    prompts = cfg.get("prompts")
    if not isinstance(prompts, dict):
        raise RuntimeError("Missing [prompts] table in prompt config")
    return _require_str(prompts.get(name), field=f"prompts.{name}")


def _style_templates() -> dict[str, str]:
    cfg = _load_config()
    styles = cfg.get("style_templates")
    if not isinstance(styles, dict):
        raise RuntimeError("Missing [style_templates] table in prompt config")
    out: dict[str, str] = {}
    for key, value in styles.items():
        out[str(key)] = _require_str(value, field=f"style_templates.{key}")
    return out


def get_storyboard_system_prompt() -> str:
    return _prompt_value("storyboard_system")


def get_storyboard_retry_suffix() -> str:
    return _prompt_value("storyboard_retry_suffix")


def style_prompt(style_template: str) -> str:
    style_templates = _style_templates()
    try:
        return style_templates[style_template]
    except KeyError as exc:
        raise ValueError(f"Unknown style_template: {style_template!r}") from exc


def build_storyboard_user_prompt(req: TeaserRequest) -> str:
    template = _prompt_value("storyboard_user")
    return template.format(
        output_language=req.output_language,
        style_template=req.style_template,
        source_text=req.source_text,
    )


def build_anchor_image_prompt(plan: TeaserPlan) -> str:
    style = style_prompt(plan.style_template)
    negative_hint = _prompt_value("negative_hint")
    # The model output is expected to provide a concise, reusable anchor prompt.
    anchor = plan.character_anchor_prompt.strip()
    if not anchor:
        anchor = (
            f"Main character: {plan.main_character.name}. "
            f"Keywords: {plan.main_character.visual_keywords}."
        )
    template = _prompt_value("anchor_image")
    return template.format(style=style, anchor=anchor, negative_hint=negative_hint)


def _bubble_lines(panel: Panel) -> str:
    bubbles = [b.strip() for b in panel.speech_bubbles if b.strip()]
    if not bubbles:
        return "No speech bubbles."
    return "\n".join([f"\"{b}\"" for b in bubbles])


def build_grid_image_prompt(plan: TeaserPlan) -> str:
    """Build a single prompt for a 3x3 grid image containing all 9 panels."""
    style = style_prompt(plan.style_template)
    negative_hint = _prompt_value("negative_hint")

    panels_lines: list[str] = []
    for panel in sorted(plan.panels, key=lambda p: p.index):
        bubbles = _bubble_lines(panel)
        narration = (panel.narration or "").strip() or "None"
        panels_lines.append(
            f"Panel {panel.index}: {panel.visual.strip()} "
            f"| Speech: {bubbles} | Narration: {narration}"
        )

    panels_description = "\n".join(panels_lines)
    template = _prompt_value("grid_image")
    return template.format(
        style=style,
        panels_description=panels_description,
        output_language=plan.output_language,
        negative_hint=negative_hint,
    )


def build_panel_image_prompt(plan: TeaserPlan, panel: Panel) -> str:
    style = style_prompt(plan.style_template)
    bubbles = _bubble_lines(panel)
    narration = (panel.narration or "").strip()
    narration_line = narration if narration else "None"
    negative_hint = _prompt_value("negative_hint")
    template = _prompt_value("panel_image")
    return template.format(
        style=style,
        visual=panel.visual.strip(),
        output_language=plan.output_language,
        bubbles=bubbles,
        narration=narration_line,
        negative_hint=negative_hint,
    )
