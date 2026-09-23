"""
POST /api/storage-analysis -- exposes the EXISTING BioVault storage
analysis (app.modules.storage_analysis.analyze_storage_efficiency) over
HTTP. No calculation is duplicated here.
"""

from fastapi import APIRouter

from app.modules.storage_analysis import analyze_storage_efficiency
from backend.schemas import StorageAnalysisRequest, StorageAnalysisResponse
from backend.services.biovault_service import call_core

router = APIRouter()


@router.post("/storage-analysis", response_model=StorageAnalysisResponse)
def storage_analysis(request: StorageAnalysisRequest) -> StorageAnalysisResponse:
    result = call_core(
        analyze_storage_efficiency,
        request.file_size_bytes,
        request.dna_length,
        request.block_size,
        request.redundancy_size,
        None,
    )

    return StorageAnalysisResponse(
        file_size_bytes=result["file_size_bytes"],
        binary_info=result["binary_info"],
        dna_size_info=result["dna_size_info"],
        capacity_info=result["capacity_info"],
        encoding_overhead=result["encoding_overhead"],
        raw_efficiency_percent=result["raw_efficiency_percent"],
        redundancy_info=result["redundancy_info"],
        mutation_info=result["mutation_info"],
    )
