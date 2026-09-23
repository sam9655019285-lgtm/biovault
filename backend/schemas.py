"""
Pydantic request/response models for the BioVault backend API.

These schemas describe the SAME data shapes the existing core modules
already return (see app/modules/dna_encoder.py, dna_decoder.py,
dna_mutator.py, dna_error_correction.py, storage_analysis.py) -- they
do not introduce new fields or alternate meanings for existing ones.
Kept simple and flat wherever the underlying dict already is; nested
dicts that are themselves clearly-documented existing structures
(e.g. storage_analysis's sub-reports) are passed through as
Dict[str, Any] rather than re-declared field-by-field, to avoid a
second, maintenance-prone copy of their shape.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.modules.dna_error_correction import DEFAULT_BLOCK_SIZE, DEFAULT_REDUNDANCY_SIZE
from app.modules.dna_mutator import MUTATION_TYPES


class HealthResponse(BaseModel):
    status: str
    service: str


# --- Encoding --------------------------------------------------------------------

class EncodeRequest(BaseModel):
    data_base64: str = Field(..., description="Base64-encoded file bytes to encode into DNA.")
    filename: Optional[str] = Field(None, description="Optional source filename, echoed back for identity purposes.")


class EncodeResponse(BaseModel):
    source_filename: Optional[str]
    content_hash: str
    original_size_bytes: int
    binary_length_bits: int
    dna_sequence: str
    dna_length: int
    bits_per_base: int
    base_counts: dict


# --- Decoding --------------------------------------------------------------------

class DecodeRequest(BaseModel):
    dna_sequence: str = Field(..., description="DNA sequence (A/T/G/C) to decode back into bytes.")


class DecodeResponse(BaseModel):
    dna_length: int
    binary_length_bits: int
    recovered_bytes_base64: str
    recovered_size_bytes: int


# --- Mutation ----------------------------------------------------------------------

class MutationRequest(BaseModel):
    dna_sequence: str = Field(..., description="DNA sequence to mutate.")
    mutation_type: str = Field(..., description=f"One of: {', '.join(MUTATION_TYPES)}.")
    mutation_rate: float = Field(..., ge=0, le=100, description="Mutation rate as a percentage (0-100).")
    seed: Optional[int] = Field(None, description="Optional random seed for reproducible results.")


class MutationResponse(BaseModel):
    mutated_sequence: str
    mutation_type: str
    mutation_rate: float
    seed: Optional[int]
    original_length: int
    mutated_length: int
    substitutions: int
    insertions: int
    deletions: int
    total_edits: int
    edit_rate_percent: float


# --- Error correction ----------------------------------------------------------------

class ErrorCorrectionRequest(BaseModel):
    dna_sequence: str = Field(..., description="Original DNA sequence to protect with redundancy.")
    received_sequence: Optional[str] = Field(
        None,
        description="Optional already-protected (possibly corrupted) sequence to detect/correct. "
        "If omitted, the freshly protected sequence itself is used (no simulated errors).",
    )
    block_size: int = Field(DEFAULT_BLOCK_SIZE, ge=1, description="Bases per checksum block.")
    redundancy_size: int = Field(DEFAULT_REDUNDANCY_SIZE, ge=1, description="Checksum bases per block.")


class ErrorCorrectionResponse(BaseModel):
    protected_sequence: str
    received_sequence: str
    block_size: int
    redundancy_size: int
    detection: dict
    correction: dict


# --- Storage analysis ------------------------------------------------------------------

class StorageAnalysisRequest(BaseModel):
    file_size_bytes: int = Field(..., ge=0)
    dna_length: int = Field(..., ge=0)
    block_size: Optional[int] = Field(None, ge=1)
    redundancy_size: Optional[int] = Field(None, ge=1)


class StorageAnalysisResponse(BaseModel):
    file_size_bytes: int
    binary_info: dict
    dna_size_info: dict
    capacity_info: dict
    encoding_overhead: dict
    raw_efficiency_percent: float
    redundancy_info: Optional[dict]
    mutation_info: Optional[dict]


class ErrorResponse(BaseModel):
    detail: str
