from __future__ import annotations

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from google import genai
from sse_starlette.sse import EventSourceResponse

from app.shared.client import get_genai_client
from app.shared.database import get_db
from app.domain.conti.schemas import ContiRequest, GenerateMediaRequest, GenerateMediaResponse, RunSummary, RunDetail
from app.domain.conti.service import ContiOrchestratorService
from app.domain.conti.repository import PipelineRepository

router = APIRouter(prefix="/api/pipeline", tags=["conti"])


def _get_service(client: genai.Client = Depends(get_genai_client)) -> ContiOrchestratorService:
    return ContiOrchestratorService(client)


async def _get_repo(db: aiosqlite.Connection = Depends(get_db)) -> PipelineRepository:
    return PipelineRepository(db)


@router.post("/generate")
async def generate_conti(
    request: ContiRequest,
    service: ContiOrchestratorService = Depends(_get_service),
    repo: PipelineRepository = Depends(_get_repo),
) -> EventSourceResponse:
    run_id = await repo.create_run(request)

    async def event_stream():
        yield service._sse_event("run_created", {"run_id": run_id})
        async for event in service.generate_and_persist(request, run_id, repo):
            yield event

    return EventSourceResponse(event_stream())


@router.post("/step/generate-media", response_model=GenerateMediaResponse)
async def generate_media(
    request: GenerateMediaRequest,
    service: ContiOrchestratorService = Depends(_get_service),
) -> GenerateMediaResponse:
    return await service.generate_media_batch(request)


@router.get("/runs", response_model=list[RunSummary])
async def list_runs(repo: PipelineRepository = Depends(_get_repo)) -> list[RunSummary]:
    rows = await repo.list_runs()
    return [RunSummary(**r) for r in rows]


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(
    run_id: str, repo: PipelineRepository = Depends(_get_repo)
) -> RunDetail:
    result = await repo.get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunDetail(**result)
