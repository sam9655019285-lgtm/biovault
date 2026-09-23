"""
POST /api/error-correction -- exposes the EXISTING BioVault Phase 6
checksum-based error correction (app.modules.dna_error_correction) over
HTTP: add_redundancy() -> detect_errors() -> correct_substitution_errors().

No error-correction algorithm is reimplemented here; block-size
behavior, correction behavior, failure behavior, and validation are
all identical to the Streamlit Error Correction page because the same
functions are called directly.
"""

from fastapi import APIRouter

from app.modules.dna_error_correction import (
    add_redundancy,
    detect_errors,
    correct_substitution_errors,
)
from backend.schemas import ErrorCorrectionRequest, ErrorCorrectionResponse
from backend.services.biovault_service import call_core

router = APIRouter()


@router.post("/error-correction", response_model=ErrorCorrectionResponse)
def error_correction(request: ErrorCorrectionRequest) -> ErrorCorrectionResponse:
    protection = call_core(
        add_redundancy, request.dna_sequence, request.block_size, request.redundancy_size
    )
    protected_sequence = protection["protected_sequence"]
    original_length = protection["original_length"]

    received_sequence = request.received_sequence or protected_sequence

    detection = call_core(
        detect_errors, received_sequence, request.block_size, request.redundancy_size, original_length
    )
    correction = call_core(
        correct_substitution_errors,
        received_sequence,
        request.block_size,
        request.redundancy_size,
        original_length,
    )

    return ErrorCorrectionResponse(
        protected_sequence=protected_sequence,
        received_sequence=received_sequence,
        block_size=request.block_size,
        redundancy_size=request.redundancy_size,
        detection=detection,
        correction=correction,
    )
