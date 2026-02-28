from __future__ import annotations

from fastapi import APIRouter, Depends
from google import genai

from app.shared.client import get_genai_client
from app.domain.validator.schemas import ValidationRequest, ValidationReport
from app.domain.validator.service import ValidatorService

router = APIRouter(prefix="/api/pipeline", tags=["validator"])


def _get_service(client: genai.Client = Depends(get_genai_client)) -> ValidatorService:
    return ValidatorService(client)


@router.post("/validate", response_model=ValidationReport)
def validate_cut_plan(
    request: ValidationRequest,
    service: ValidatorService = Depends(_get_service),
) -> ValidationReport:
    return service.validate(request)
