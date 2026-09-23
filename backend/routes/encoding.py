"""
POST /api/encode -- exposes the EXISTING BioVault encoder
(app.modules.dna_encoder.encode_file_to_dna) over HTTP.

No encoding logic is reimplemented here.
"""

from fastapi import APIRouter

from app.modules.dna_encoder import encode_file_to_dna
from app.modules.file_handler import compute_content_hash
from backend.schemas import EncodeRequest, EncodeResponse
from backend.services.biovault_service import call_core, decode_base64_or_400

router = APIRouter()


@router.post("/encode", response_model=EncodeResponse)
def encode(request: EncodeRequest) -> EncodeResponse:
    data = decode_base64_or_400(request.data_base64)
    result = call_core(encode_file_to_dna, data)
    content_hash = call_core(compute_content_hash, data)

    return EncodeResponse(
        source_filename=request.filename,
        content_hash=content_hash,
        original_size_bytes=result["original_size_bytes"],
        binary_length_bits=result["binary_length_bits"],
        dna_sequence=result["dna_sequence"],
        dna_length=result["dna_length"],
        bits_per_base=result["bits_per_base"],
        base_counts=result["base_counts"],
    )
