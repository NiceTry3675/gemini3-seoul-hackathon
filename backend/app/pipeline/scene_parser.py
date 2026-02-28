from app.models.schemas import NovelInput, SceneBreakdown
from app.models.prompts import SCENE_PARSER_SYSTEM
from app.pipeline.gemini import call_gemini_structured


async def parse_scenes(novel_input: NovelInput) -> SceneBreakdown:
    """Step 1: Parse novel text into 2-6 visual scenes."""
    system_prompt = SCENE_PARSER_SYSTEM.format(
        output_language=novel_input.output_language,
    )
    user_prompt = f"""Genre: {novel_input.genre.value}
Tone: {novel_input.tone.value}
Rating: {novel_input.rating.value}

Novel text:
{novel_input.manuscript}"""

    return await call_gemini_structured(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=SceneBreakdown,
    )
