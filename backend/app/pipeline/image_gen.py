import asyncio

from app.models.schemas import CharacterSheet, CutPlan, GeneratedCut, Cut
from app.models.prompts import (
    IMAGE_PROMPT_TEMPLATE,
    TONE_STYLE_MAP,
    RATING_GUIDANCE_MAP,
)
from app.pipeline.gemini import generate_image

BATCH_SIZE = 3
BATCH_DELAY_SEC = 2
MAX_RETRIES = 3


def _build_image_prompt(
    cut: Cut,
    characters: CharacterSheet,
    tone: str,
    rating: str,
) -> str:
    """Build a detailed image generation prompt for a single cut."""
    char_descriptions = []
    for char_name in cut.characters_in_frame:
        for char in characters.characters:
            if char.name == char_name or char.name_en == char_name:
                appearance = ", ".join(char.appearance_keywords)
                char_descriptions.append(
                    f"- {char.name_en}: {appearance} (personality: {char.personality_one_word})"
                )
                break
        else:
            char_descriptions.append(f"- {char_name}")

    return IMAGE_PROMPT_TEMPLATE.format(
        tone_style=TONE_STYLE_MAP.get(tone, TONE_STYLE_MAP["emotional"]),
        camera=cut.camera,
        mood=cut.mood,
        background=cut.background,
        character_descriptions=(
            "\n".join(char_descriptions)
            if char_descriptions
            else "No characters in frame"
        ),
        action=cut.action,
        rating_guidance=RATING_GUIDANCE_MAP.get(rating, RATING_GUIDANCE_MAP["all"]),
    )


async def generate_cut_image(
    cut: Cut,
    characters: CharacterSheet,
    tone: str,
    rating: str,
) -> GeneratedCut:
    """Generate image for a single cut with retries."""
    prompt = _build_image_prompt(cut, characters, tone, rating)

    for attempt in range(MAX_RETRIES):
        image_b64 = await generate_image(prompt)
        if image_b64:
            return GeneratedCut(
                cut_id=cut.id,
                image_base64=image_b64,
                prompt_used=prompt,
            )
        # Slightly modify prompt on retry
        if attempt < MAX_RETRIES - 1:
            prompt = (
                prompt
                + f"\n\n(Attempt {attempt + 2}: Please generate a clear illustration.)"
            )
            await asyncio.sleep(1)

    # Return empty image on total failure
    return GeneratedCut(
        cut_id=cut.id,
        image_base64="",
        prompt_used=prompt,
    )


async def generate_all_images(
    cut_plan: CutPlan,
    characters: CharacterSheet,
    tone: str,
    rating: str,
    progress_callback=None,
) -> list[GeneratedCut]:
    """Step 5: Generate images for all 12 cuts in batches."""
    results: list[GeneratedCut] = []

    for batch_start in range(0, len(cut_plan.cuts), BATCH_SIZE):
        batch = cut_plan.cuts[batch_start : batch_start + BATCH_SIZE]

        batch_tasks = [
            generate_cut_image(cut, characters, tone, rating) for cut in batch
        ]
        batch_results = await asyncio.gather(*batch_tasks)
        results.extend(batch_results)

        if progress_callback:
            await progress_callback(
                f"Generated images {batch_start + 1}-{batch_start + len(batch)} of {len(cut_plan.cuts)}"
            )

        # Delay between batches to respect rate limits
        if batch_start + BATCH_SIZE < len(cut_plan.cuts):
            await asyncio.sleep(BATCH_DELAY_SEC)

    return results
