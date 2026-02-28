from __future__ import annotations

from fastapi import APIRouter, Depends
from google import genai

from app.shared.client import get_genai_client
from app.domain.cut_planner.schemas import CutPlanRequest, CutPlan
from app.domain.cut_planner.service import CutPlannerService

router = APIRouter(prefix="/api/pipeline", tags=["cut_planner"])


def _get_service(client: genai.Client = Depends(get_genai_client)) -> CutPlannerService:
    return CutPlannerService(client)


@router.post("/cut-plan", response_model=CutPlan)
def create_cut_plan(
    request: CutPlanRequest,
    service: CutPlannerService = Depends(_get_service),
) -> CutPlan:
    return service.plan(request)
