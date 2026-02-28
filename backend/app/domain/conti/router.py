from __future__ import annotations

from fastapi import APIRouter, Depends
from google import genai
from sse_starlette.sse import EventSourceResponse

from app.shared.client import get_genai_client
from app.domain.conti.schemas import ContiRequest
from app.domain.conti.service import ContiOrchestratorService

router = APIRouter(prefix="/api/pipeline", tags=["conti"])


def _get_service(client: genai.Client = Depends(get_genai_client)) -> ContiOrchestratorService:
    return ContiOrchestratorService(client)


@router.post("/generate")
async def generate_conti(
    request: ContiRequest,
    service: ContiOrchestratorService = Depends(_get_service),
) -> EventSourceResponse:
    return EventSourceResponse(service.generate(request))
