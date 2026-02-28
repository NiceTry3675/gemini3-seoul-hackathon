from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

import tomllib
import yaml
from jinja2 import Environment, BaseLoader

_BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
_SYSTEM_INSTRUCTION_PATH = _BASE_DIR / "system_instruction.toml"
_PROMPTS_DIR = _BASE_DIR / "prompts"


class PromptManager:
    def __init__(self) -> None:
        self._system_cache: dict | None = None
        self._template_cache: dict[str, str] = {}
        self._jinja_env = Environment(loader=BaseLoader())
        self._is_prod = os.getenv("ENV", "dev") == "prod"

    def _load_system_instructions(self) -> dict:
        if self._system_cache is not None and self._is_prod:
            return self._system_cache
        with open(_SYSTEM_INSTRUCTION_PATH, "rb") as f:
            self._system_cache = tomllib.load(f)
        return self._system_cache

    def get_system_instruction(self, key: str) -> str:
        """Get system instruction by dotted key (e.g. 'scene_parser.instruction')."""
        data = self._load_system_instructions()
        parts = key.split(".")
        current = data
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                raise KeyError(f"System instruction key not found: {key}")
            current = current[part]
        if not isinstance(current, str):
            raise ValueError(f"System instruction at '{key}' is not a string")
        return current

    def _load_template(self, template_name: str) -> str:
        if template_name in self._template_cache and self._is_prod:
            return self._template_cache[template_name]
        path = _PROMPTS_DIR / f"{template_name}.yaml"
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        template_str = data.get("template", "")
        self._template_cache[template_name] = template_str
        return template_str

    def render(self, template_name: str, **variables) -> str:
        """Load YAML template and render with Jinja2 variables."""
        raw = self._load_template(template_name)
        template = self._jinja_env.from_string(raw)
        return template.render(**variables)


@lru_cache(maxsize=1)
def get_prompt_manager() -> PromptManager:
    return PromptManager()
