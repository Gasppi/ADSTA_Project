from typing import Annotated

from fastapi import APIRouter, Depends

from credit_backend.contracts import DecisionRequest, DecisionResponse
from credit_backend.decisions.dependencies import get_service
from credit_backend.decisions.service import DecisionService

router = APIRouter()


@router.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@router.post('/decisions')
def create_decision(service: Annotated[DecisionService, Depends(get_service)], request: DecisionRequest) -> DecisionResponse:
    return service.decide(request)
