import asyncio
from typing import Callable, Awaitable, Any

from app.models.schemas import NovelInput, ContiResult
from app.pipeline.scene_parser import parse_scenes
from app.pipeline.character_gen import generate_characters, generate_character_refs
from app.pipeline.cut_planner import plan_cuts
from app.pipeline.validator import validate_cuts
from app.pipeline.image_gen import generate_all_images


async def generate_conti(
    novel_input: NovelInput,
    emit: Callable[[int, str, str, Any], Awaitable[None]],
) -> ContiResult:
    """
    Run the full 5-step pipeline to generate a webtoon conti.

    emit(step, name, status, data) is called for SSE progress updates.
    """
    # Step 1: Scene parsing
    await emit(1, "Scene Parsing", "running", None)
    scenes = await parse_scenes(novel_input)
    await emit(1, "Scene Parsing", "done", scenes.model_dump())

    # Step 2: Character generation
    await emit(2, "Character Generation", "running", None)
    characters = await generate_characters(scenes, novel_input)
    char_refs = await generate_character_refs(characters)
    await emit(
        2,
        "Character Generation",
        "done",
        {"characters": characters.model_dump(), "reference_images": len(char_refs)},
    )

    # Step 3: 12-cut planning
    await emit(3, "Cut Planning", "running", None)
    cut_plan = await plan_cuts(scenes, characters, novel_input)
    await emit(3, "Cut Planning", "done", cut_plan.model_dump())

    # Step 4: Validation
    await emit(4, "Validation", "running", None)
    validation = await validate_cuts(cut_plan, characters)
    if not validation.all_passed:
        # Re-plan with lower temperature on failure
        await emit(4, "Validation", "running", {"retrying": True})
        cut_plan = await plan_cuts(scenes, characters, novel_input)
        validation = await validate_cuts(cut_plan, characters)
    await emit(4, "Validation", "done", validation.model_dump())

    # Step 5: Image generation
    await emit(5, "Image Generation", "running", None)

    async def image_progress(msg: str):
        await emit(5, "Image Generation", "running", {"progress": msg})

    images = await generate_all_images(
        cut_plan,
        characters,
        tone=novel_input.tone.value,
        rating=novel_input.rating.value,
        progress_callback=image_progress,
    )
    await emit(5, "Image Generation", "done", {"count": len(images)})

    return ContiResult(
        characters=characters,
        cuts=cut_plan,
        images=images,
    )
