import asyncio
import json
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.models.schemas import NovelInput, ContiResult, GeneratedCut
from app.pipeline.orchestrator import generate_conti
from app.pipeline.image_gen import generate_cut_image

app = FastAPI(title="Novel → Webtoon Conti Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory task storage
tasks: dict[str, dict] = {}


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/generate")
async def start_generation(novel_input: NovelInput):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "running",
        "input": novel_input,
        "events": [],
        "result": None,
        "error": None,
    }

    async def run():
        try:

            async def emit(step: int, name: str, status: str, data: Any):
                event = {
                    "step": step,
                    "name": name,
                    "status": status,
                    "data": data,
                }
                tasks[task_id]["events"].append(event)

            result = await generate_conti(novel_input, emit)
            tasks[task_id]["result"] = result
            tasks[task_id]["status"] = "done"
        except Exception as e:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = str(e)
            tasks[task_id]["events"].append(
                {"step": 0, "name": "error", "status": "error", "data": str(e)}
            )

    asyncio.create_task(run())
    return {"task_id": task_id}


@app.get("/api/progress/{task_id}")
async def stream_progress(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_stream():
        sent = 0
        while True:
            task = tasks[task_id]
            events = task["events"]

            while sent < len(events):
                yield _sse_event(events[sent])
                sent += 1

            if task["status"] in ("done", "error"):
                yield _sse_event(
                    {"step": 0, "name": "complete", "status": task["status"]}
                )
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/result/{task_id}")
async def get_result(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    if task["status"] == "running":
        raise HTTPException(status_code=202, detail="Still processing")
    if task["status"] == "error":
        raise HTTPException(status_code=500, detail=task["error"])

    result: ContiResult = task["result"]
    return result.model_dump()


@app.post("/api/regenerate-cut/{task_id}/{cut_id}")
async def regenerate_cut(task_id: str, cut_id: int):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    if task["status"] != "done" or task["result"] is None:
        raise HTTPException(status_code=400, detail="Task not complete")

    result: ContiResult = task["result"]
    novel_input: NovelInput = task["input"]

    # Find the cut
    target_cut = None
    for cut in result.cuts.cuts:
        if cut.id == cut_id:
            target_cut = cut
            break

    if target_cut is None:
        raise HTTPException(status_code=404, detail=f"Cut {cut_id} not found")

    new_image = await generate_cut_image(
        target_cut,
        result.characters,
        tone=novel_input.tone.value,
        rating=novel_input.rating.value,
    )

    # Update stored result
    for i, img in enumerate(result.images):
        if img.cut_id == cut_id:
            result.images[i] = new_image
            break

    return new_image.model_dump()
