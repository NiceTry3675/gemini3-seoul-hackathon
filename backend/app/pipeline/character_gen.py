from app.models.schemas import NovelInput, SceneBreakdown, CharacterSheet
from app.models.prompts import CHARACTER_GEN_SYSTEM
from app.pipeline.gemini import call_gemini_structured, generate_image


async def generate_characters(
    scenes: SceneBreakdown, novel_input: NovelInput
) -> CharacterSheet:
    """Step 2a: Generate character sheets from scene breakdown."""
    scenes_text = "\n".join(
        f"Scene {s.scene_id}: {s.summary} (characters: {', '.join(s.characters_present)})"
        for s in scenes.scenes
    )
    user_prompt = f"""Genre: {novel_input.genre.value}
Tone: {novel_input.tone.value}

Scenes:
{scenes_text}"""

    return await call_gemini_structured(
        system_prompt=CHARACTER_GEN_SYSTEM,
        user_prompt=user_prompt,
        response_schema=CharacterSheet,
    )


async def generate_character_refs(characters: CharacterSheet) -> dict[str, str]:
    """Step 2b: Generate reference images for each character. Returns name → base64."""
    refs: dict[str, str] = {}
    for char in characters.characters:
        appearance = ", ".join(char.appearance_keywords)
        prompt = (
            f"Character reference sheet, webtoon style, clean white background. "
            f"Single character: {char.name_en}. "
            f"Appearance: {appearance}. "
            f"Personality: {char.personality_one_word}. "
            f"Show front-facing portrait, upper body. "
            f"No text, no labels, no speech bubbles."
        )
        image_b64 = await generate_image(prompt)
        if image_b64:
            refs[char.name] = image_b64
    return refs
