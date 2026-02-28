from app.models.schemas import (
    NovelInput,
    SceneBreakdown,
    CharacterSheet,
    CutPlan,
)
from app.models.prompts import CUT_PLANNER_SYSTEM
from app.pipeline.gemini import call_gemini_structured


async def plan_cuts(
    scenes: SceneBreakdown,
    characters: CharacterSheet,
    novel_input: NovelInput,
) -> CutPlan:
    """Step 3: Create a 12-cut storyboard plan."""
    system_prompt = CUT_PLANNER_SYSTEM.format(
        output_language=novel_input.output_language,
    )

    scenes_text = "\n".join(
        f"Scene {s.scene_id}: {s.summary} | emotion: {s.emotion} | "
        f"action: {s.key_action} | bg: {s.background} | "
        f"characters: {', '.join(s.characters_present)}"
        for s in scenes.scenes
    )

    chars_text = "\n".join(
        f"- {c.name} ({c.name_en}): {', '.join(c.appearance_keywords)} | "
        f"personality: {c.personality_one_word}"
        for c in characters.characters
    )

    user_prompt = f"""Genre: {novel_input.genre.value}
Tone: {novel_input.tone.value}
Rating: {novel_input.rating.value}
Output language: {novel_input.output_language}

Scenes:
{scenes_text}

Characters:
{chars_text}

Create exactly 12 cuts following the rules."""

    return await call_gemini_structured(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=CutPlan,
    )
