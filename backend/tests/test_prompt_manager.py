"""Tests for app/prompt_manager.py"""
from __future__ import annotations

import textwrap
from unittest.mock import patch, MagicMock

import pytest

from app.prompt_manager import PromptManager


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_TOML_DICT = {
    "scene_parser": {"instruction": "You are a scene parser."},
    "character_gen": {"instruction": "You are a character designer."},
    "nested": {"deep": {"value": "deep value"}},
}

SAMPLE_YAML = textwrap.dedent("""\
    name: test_template
    template: |
      Topic: {{ topic }}
      Context: {{ context }}
""")


# ---------------------------------------------------------------------------
# Tests: get_system_instruction
# ---------------------------------------------------------------------------

class TestGetSystemInstruction:
    """Patch _load_system_instructions to avoid filesystem dependency."""

    def _make_pm(self) -> PromptManager:
        pm = PromptManager()
        pm._load_system_instructions = MagicMock(return_value=SAMPLE_TOML_DICT)
        return pm

    def test_simple_dotted_key(self):
        pm = self._make_pm()
        result = pm.get_system_instruction("scene_parser.instruction")
        assert result == "You are a scene parser."

    def test_another_top_level_key(self):
        pm = self._make_pm()
        result = pm.get_system_instruction("character_gen.instruction")
        assert result == "You are a character designer."

    def test_deeply_nested_key(self):
        pm = self._make_pm()
        result = pm.get_system_instruction("nested.deep.value")
        assert result == "deep value"

    def test_missing_top_level_key_raises_key_error(self):
        pm = self._make_pm()
        with pytest.raises(KeyError, match="nonexistent"):
            pm.get_system_instruction("nonexistent.key")

    def test_missing_nested_key_raises_key_error(self):
        pm = self._make_pm()
        with pytest.raises(KeyError, match="scene_parser.missing"):
            pm.get_system_instruction("scene_parser.missing")

    def test_non_string_value_raises_value_error(self):
        pm = self._make_pm()
        # "nested" maps to a dict, not a string
        with pytest.raises(ValueError, match="not a string"):
            pm.get_system_instruction("nested")

    def test_single_segment_key_not_found_raises_key_error(self):
        pm = self._make_pm()
        with pytest.raises(KeyError):
            pm.get_system_instruction("missing_top")

    def test_result_is_a_string(self):
        pm = self._make_pm()
        result = pm.get_system_instruction("scene_parser.instruction")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Tests: render (Jinja2 YAML templates)
# ---------------------------------------------------------------------------

class TestRender:
    """Patch _load_template to avoid filesystem dependency."""

    def _make_pm_with_template(self, template_str: str) -> PromptManager:
        pm = PromptManager()
        pm._load_template = MagicMock(return_value=template_str)
        return pm

    def test_renders_variables(self):
        template_str = "Topic: {{ topic }}\nContext: {{ context }}\n"
        pm = self._make_pm_with_template(template_str)
        result = pm.render("any_template", topic="AI", context="Machine learning")
        assert "Topic: AI" in result
        assert "Context: Machine learning" in result

    def test_missing_variable_renders_empty(self):
        template_str = "Topic: {{ topic }}\nContext: {{ context }}\n"
        pm = self._make_pm_with_template(template_str)
        # Jinja2 renders undefined vars as empty string by default
        result = pm.render("any_template", topic="AI")
        assert "Topic: AI" in result

    def test_empty_template(self):
        pm = self._make_pm_with_template("")
        result = pm.render("any_template", foo="bar")
        assert result == ""

    def test_template_with_no_variables(self):
        pm = self._make_pm_with_template("Hello, world!")
        result = pm.render("any_template")
        assert result == "Hello, world!"

    def test_load_template_from_filesystem(self, tmp_path):
        """_load_template reads real YAML from the prompts directory."""
        yaml_content = "template: 'Hello {{ name }}'\n"
        (tmp_path / "greet.yaml").write_text(yaml_content)

        pm = PromptManager()
        with patch("app.prompt_manager._PROMPTS_DIR", tmp_path):
            result = pm.render("greet", name="World")
        assert "Hello World" in result

    def test_load_system_instruction_from_filesystem(self, tmp_path):
        """get_system_instruction reads real TOML from disk."""
        toml_path = tmp_path / "system_instruction.toml"
        toml_path.write_text('[test_section]\ninstruction = "Test instruction"\n')

        pm = PromptManager()
        with patch("app.prompt_manager._SYSTEM_INSTRUCTION_PATH", toml_path):
            result = pm.get_system_instruction("test_section.instruction")
        assert result == "Test instruction"
