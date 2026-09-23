"""
POST /api/mutation -- exposes the EXISTING BioVault mutation simulator
(app.modules.dna_mutator.mutate_dna) over HTTP.

No mutation logic is reimplemented here; the same substitution/
insertion/deletion behavior, validation, and deterministic seeding
already used by the Streamlit Mutation Simulator page apply unchanged.
"""

from fastapi import APIRouter

from app.modules.dna_mutator import mutate_dna
from backend.schemas import MutationRequest, MutationResponse
from backend.services.biovault_service import call_core

router = APIRouter()


@router.post("/mutation", response_model=MutationResponse)
def mutation(request: MutationRequest) -> MutationResponse:
    result = call_core(
        mutate_dna,
        request.dna_sequence,
        request.mutation_type,
        request.mutation_rate,
        request.seed,
    )

    return MutationResponse(
        mutated_sequence=result["mutated_sequence"],
        mutation_type=result["mutation_type"],
        mutation_rate=result["mutation_rate"],
        seed=result["seed"],
        original_length=result["original_length"],
        mutated_length=result["mutated_length"],
        substitutions=result["substitutions"],
        insertions=result["insertions"],
        deletions=result["deletions"],
        total_edits=result["total_edits"],
        edit_rate_percent=result["edit_rate_percent"],
    )
