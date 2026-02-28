from app.models.schemas import (
    CharacterSheet,
    CutPlan,
    ValidationReport,
)
from app.models.prompts import VALIDATOR_SYSTEM
from app.pipeline.gemini import call_gemini_structured


async def validate_cuts(
    cuts: CutPlan,
    characters: CharacterSheet,
) -> ValidationReport:
    """Step 4: Validate cuts for consistency and quality."""
    chars_text = "\n".join(
        f"- {c.name} ({c.name_en}): {', '.join(c.appearance_keywords)}"
        for c in characters.characters
    )

    cuts_text = "\n".join(
        f"Cut {c.id} (scene: {c.scene_ref}): camera={c.camera}, mood={c.mood}, "
        f"action={c.action}, dialogue='{c.dialogue}' ({len(c.dialogue)} chars), "
        f"characters={', '.join(c.characters_in_frame)}, bg={c.background}"
        for c in cuts.cuts
    )

    user_prompt = f"""Characters:
{chars_text}

Cuts to validate:
{cuts_text}"""

    return await call_gemini_structured(
        system_prompt=VALIDATOR_SYSTEM,
        user_prompt=user_prompt,
        response_schema=ValidationReport,
    )
