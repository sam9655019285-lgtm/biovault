"""
POST /api/decode -- exposes the EXISTING BioVault decoder
(app.modules.dna_decoder.decode_dna_to_file) over HTTP.

No decoding logic is reimplemented here; existing validation and error
behavior (invalid characters, empty input, wrong length) is preserved
because the real function is called directly.
"""

import base64

from fastapi import APIRouter

from app.modules.dna_decoder import decode_dna_to_file
from backend.schemas import DecodeRequest, DecodeResponse
from backend.services.biovault_service import call_core

router = APIRouter()


@router.post("/decode", response_model=DecodeResponse)
def decode(request: DecodeRequest) -> DecodeResponse:
    result = call_core(decode_dna_to_file, request.dna_sequence)

    return DecodeResponse(
        dna_length=result["dna_length"],
        binary_length_bits=result["binary_length_bits"],
        recovered_bytes_base64=base64.b64encode(result["recovered_bytes"]).decode("ascii"),
        recovered_size_bytes=result["recovered_size_bytes"],
    )
