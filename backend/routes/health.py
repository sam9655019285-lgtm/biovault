"""
GET /api/health -- a trivial liveness check.

Performs no processing beyond constructing a fixed response, so it is
safe to poll frequently.
"""

from fastapi import APIRouter

from backend.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="BioVault API")
