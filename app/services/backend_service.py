"""
Backend integration layer (non-UI).

This is the ONLY place in the Streamlit application that knows whether
a core BioVault operation (encode, decode, mutate, protect/detect/
correct errors, analyze storage) runs locally (direct function call
into app/modules/*.py, as before Phase 23) or through the FastAPI
backend (api/client.py -> backend/main.py -> the SAME app/modules/*.py
functions). Every Streamlit page keeps calling these same five/eight
functions regardless of mode -- nothing about the UI needs to know or
care which mode is active.

MODE SELECTION: app.config.BIOVAULT_USE_API (env var BIOVAULT_USE_API,
default "false"). When False (the default), every function below is a
direct, zero-overhead call to the existing local implementation --
behavior is IDENTICAL to before Phase 23/24 existed.

RESULT COMPATIBILITY: every function here returns the EXACT SAME dict
shape the existing local core function already returns, whether or not
API mode is active. The backend API's response is missing a couple of
fields the UI relies on for display (`binary_str`) or uses a transport
encoding (`recovered_bytes_base64` instead of raw `recovered_bytes`) --
this layer normalizes those differences using the existing, already-
tested pure helper functions (dna_encoder.bytes_to_binary,
dna_decoder.dna_to_binary) rather than inventing anything new.

ERROR COMPATIBILITY: when the backend returns a validation error (HTTP
400/422), it is re-raised here as the SAME exception type the local
function would have raised (DNAEncodingError, DNADecodingError, etc.),
with the same message -- so every existing `except DNAEncodingError`
block in the UI keeps working completely unchanged in both modes. A
genuine connectivity failure (backend unreachable) is raised as
BackendUnavailableError instead, which is a NEW, distinct exception
the UI is expected to catch separately to show the required fallback
message and then retry locally (see Step 11 of Phase 24).
"""

from app.config import BIOVAULT_API_URL, BIOVAULT_USE_API
from app.modules.dna_encoder import DNAEncodingError, bytes_to_binary, encode_file_to_dna
from app.modules.dna_decoder import DNADecodingError, dna_to_binary, decode_dna_to_file
from app.modules.dna_mutator import DNAMutationError, mutate_dna
from app.modules.dna_error_correction import (
    DNAErrorCorrectionError,
    add_redundancy,
    detect_errors,
    correct_substitution_errors,
)
from app.modules.storage_analysis import (
    StorageAnalysisError,
    analyze_storage_efficiency,
    calculate_mutation_impact,
)

from api.client import BioVaultAPIClientError, is_backend_available
from api import client as api_client


class BackendUnavailableError(Exception):
    """Raised when BIOVAULT_USE_API is true but the backend API could
    not be reached (a connectivity/availability failure, NOT a
    validation error the backend itself reported)."""


def is_api_mode() -> bool:
    """Return whether the application is currently configured to use
    the backend API (BIOVAULT_USE_API)."""
    return BIOVAULT_USE_API


def backend_status() -> dict:
    """Lightweight status for UI display: whether API mode is enabled,
    the configured API URL, and (only when API mode is enabled) whether
    the backend actually responds right now. Never raises."""
    if not BIOVAULT_USE_API:
        return {"api_mode": False, "api_url": BIOVAULT_API_URL, "backend_available": None}
    return {"api_mode": True, "api_url": BIOVAULT_API_URL, "backend_available": is_backend_available(BIOVAULT_API_URL)}


def _raise_as_connection_or_reraise(exc: BioVaultAPIClientError, domain_error_cls):
    """Translate a BioVaultAPIClientError into either BackendUnavailableError
    (no status_code -> a connection/availability failure) or the given
    domain exception class (status_code set -> a real validation error
    the backend correctly reported, which must stay visible as such)."""
    if exc.status_code is None:
        raise BackendUnavailableError(str(exc)) from exc
    raise domain_error_cls(str(exc)) from exc


# --- Encoding ----------------------------------------------------------------------

def encode(data: bytes) -> dict:
    """Encode `data` into DNA -- locally, or via the backend API,
    depending on BIOVAULT_USE_API. Returns the same dict shape as
    dna_encoder.encode_file_to_dna()."""
    if not BIOVAULT_USE_API:
        return encode_file_to_dna(data)

    try:
        result = api_client.encode(api_client.to_base64(data), base_url=BIOVAULT_API_URL)
    except BioVaultAPIClientError as exc:
        _raise_as_connection_or_reraise(exc, DNAEncodingError)

    return {
        "original_size_bytes": result["original_size_bytes"],
        "binary_length_bits": result["binary_length_bits"],
        "binary_str": bytes_to_binary(data),
        "dna_sequence": result["dna_sequence"],
        "dna_length": result["dna_length"],
        "bits_per_base": result["bits_per_base"],
        "base_counts": result["base_counts"],
    }


# --- Decoding ----------------------------------------------------------------------

def decode(dna_sequence: str) -> dict:
    """Decode `dna_sequence` back into bytes -- locally or via the
    backend API. Returns the same dict shape as
    dna_decoder.decode_dna_to_file()."""
    if not BIOVAULT_USE_API:
        return decode_dna_to_file(dna_sequence)

    try:
        result = api_client.decode(dna_sequence, base_url=BIOVAULT_API_URL)
    except BioVaultAPIClientError as exc:
        _raise_as_connection_or_reraise(exc, DNADecodingError)

    return {
        "dna_length": result["dna_length"],
        "binary_length_bits": result["binary_length_bits"],
        "binary_str": dna_to_binary(dna_sequence),
        "recovered_bytes": api_client.from_base64(result["recovered_bytes_base64"]),
        "recovered_size_bytes": result["recovered_size_bytes"],
    }


# --- Mutation ----------------------------------------------------------------------

def mutate(sequence: str, mutation_type: str, mutation_rate: float, seed=None) -> dict:
    """Apply a mutation -- locally or via the backend API. Returns the
    same dict shape as dna_mutator.mutate_dna()."""
    if not BIOVAULT_USE_API:
        return mutate_dna(sequence, mutation_type, mutation_rate, seed)

    try:
        result = api_client.mutate(sequence, mutation_type, mutation_rate, seed, base_url=BIOVAULT_API_URL)
    except BioVaultAPIClientError as exc:
        _raise_as_connection_or_reraise(exc, DNAMutationError)

    return {
        "mutated_sequence": result["mutated_sequence"],
        "mutation_type": result["mutation_type"],
        "mutation_rate": result["mutation_rate"],
        "seed": result["seed"],
        "original_length": result["original_length"],
        "mutated_length": result["mutated_length"],
        "substitutions": result["substitutions"],
        "insertions": result["insertions"],
        "deletions": result["deletions"],
        "total_edits": result["total_edits"],
        "edit_rate_percent": result["edit_rate_percent"],
    }


# --- Error correction ----------------------------------------------------------------

def protect_dna(sequence: str, block_size: int, redundancy_size: int) -> dict:
    """Add checksum redundancy -- locally or via the backend API (as
    part of /api/error-correction). Returns the same dict shape as
    dna_error_correction.add_redundancy()."""
    if not BIOVAULT_USE_API:
        return add_redundancy(sequence, block_size, redundancy_size)

    try:
        result = api_client.correct_errors(
            sequence, received_sequence=None, block_size=block_size, redundancy_size=redundancy_size,
            base_url=BIOVAULT_API_URL,
        )
    except BioVaultAPIClientError as exc:
        _raise_as_connection_or_reraise(exc, DNAErrorCorrectionError)

    protected_sequence = result["protected_sequence"]
    return {
        "protected_sequence": protected_sequence,
        "original_length": len(sequence),
        "block_size": block_size,
        "redundancy_size": redundancy_size,
    }


def detect_dna_errors(original_sequence: str, received_sequence: str, block_size: int, redundancy_size: int) -> dict:
    """Detect errors in `received_sequence` -- locally or via the
    backend API. Returns the same dict shape as
    dna_error_correction.detect_errors().

    Takes `original_sequence` (the real, unprotected DNA data) rather
    than a bare `original_length` integer: the backend's single
    /api/error-correction endpoint always re-derives the expected
    protected length by running add_redundancy() on a real sequence
    (deterministically producing the same protected_sequence as
    protect_dna() above), so it needs the actual original sequence,
    not just its length, to check `received_sequence` against.
    """
    if not BIOVAULT_USE_API:
        return detect_errors(received_sequence, block_size, redundancy_size, len(original_sequence))

    try:
        result = api_client.correct_errors(
            original_sequence, received_sequence=received_sequence, block_size=block_size,
            redundancy_size=redundancy_size, base_url=BIOVAULT_API_URL,
        )
    except BioVaultAPIClientError as exc:
        _raise_as_connection_or_reraise(exc, DNAErrorCorrectionError)

    return result["detection"]


def correct_dna_errors(original_sequence: str, received_sequence: str, block_size: int, redundancy_size: int) -> dict:
    """Attempt to correct errors in `received_sequence` -- locally or
    via the backend API. Returns the same dict shape as
    dna_error_correction.correct_substitution_errors(). See
    detect_dna_errors() for why `original_sequence` (not a bare length)
    is required in API mode."""
    if not BIOVAULT_USE_API:
        return correct_substitution_errors(received_sequence, block_size, redundancy_size, len(original_sequence))

    try:
        result = api_client.correct_errors(
            original_sequence, received_sequence=received_sequence, block_size=block_size,
            redundancy_size=redundancy_size, base_url=BIOVAULT_API_URL,
        )
    except BioVaultAPIClientError as exc:
        _raise_as_connection_or_reraise(exc, DNAErrorCorrectionError)

    return result["correction"]


# --- Storage analysis ------------------------------------------------------------------

def analyze_storage(
    file_size_bytes: int,
    dna_length: int,
    block_size: int = None,
    redundancy_size: int = None,
    mutation_stats: dict = None,
) -> dict:
    """Compute storage-efficiency figures -- locally or via the backend
    API. Returns the same dict shape as
    storage_analysis.analyze_storage_efficiency().

    The backend's /api/storage-analysis endpoint does not accept
    `mutation_stats` (Phase 23's schema only covers file size, DNA
    length, and redundancy settings). Rather than changing that
    endpoint or duplicating its math, the mutation-impact section is
    computed locally here (reusing the existing, already-tested
    storage_analysis.calculate_mutation_impact()) and merged into the
    API's response when mutation_stats is provided.
    """
    if not BIOVAULT_USE_API:
        return analyze_storage_efficiency(file_size_bytes, dna_length, block_size, redundancy_size, mutation_stats)

    try:
        result = api_client.analyze_storage(
            file_size_bytes, dna_length, block_size, redundancy_size, base_url=BIOVAULT_API_URL
        )
    except BioVaultAPIClientError as exc:
        _raise_as_connection_or_reraise(exc, StorageAnalysisError)

    if mutation_stats is not None:
        result["mutation_info"] = calculate_mutation_impact(mutation_stats)

    return result
