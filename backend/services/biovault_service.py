"""
Thin service helper for the BioVault backend API.

This module does NOT reimplement any BioVault logic. Its only job is
shared plumbing every route needs: converting the existing core
modules' domain-specific exceptions (DNAEncodingError,
DNADecodingError, DNAMutationError, DNAErrorCorrectionError,
StorageAnalysisError, FileHandlerError) into proper HTTP responses,
so a caller gets a clean 400 with a readable message instead of a
500 with an internal stack trace. All actual encoding, decoding,
mutation, error-correction, and storage-analysis logic still lives
exclusively in app/modules/*.py -- exactly as it does for the
Streamlit UI.
"""

from fastapi import HTTPException

from app.config import BIOVAULT_MAX_UPLOAD_MB
from app.modules.dna_encoder import DNAEncodingError
from app.modules.dna_decoder import DNADecodingError
from app.modules.dna_mutator import DNAMutationError
from app.modules.dna_error_correction import DNAErrorCorrectionError
from app.modules.storage_analysis import StorageAnalysisError
from app.modules.file_handler import FileHandlerError

# Every domain exception BioVault's existing core modules can raise for
# invalid *input* (as opposed to an unexpected internal bug) -- mapped
# to HTTP 400, never 500, since these represent the caller's mistake,
# not a server fault.
_DOMAIN_ERRORS = (
    DNAEncodingError,
    DNADecodingError,
    DNAMutationError,
    DNAErrorCorrectionError,
    StorageAnalysisError,
    FileHandlerError,
)


def call_core(func, *args, **kwargs):
    """Call an existing BioVault core function and translate its
    documented domain exceptions into HTTPException(400, ...).

    Any OTHER, unexpected exception is re-raised as-is so FastAPI's own
    default handler turns it into a generic 500 without ever echoing
    Python internals back to the caller (see backend/main.py's
    exception handler).
    """
    try:
        return func(*args, **kwargs)
    except _DOMAIN_ERRORS as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def decode_base64_or_400(raw_base64: str, field_name: str = "data_base64") -> bytes:
    """Decode a base64 string into bytes, enforcing BIOVAULT_MAX_UPLOAD_MB
    on the actual decoded size, or raise a clean HTTP 400.

    This is the route-level, authoritative size check (the request-wide
    Content-Length check in backend/main.py's MaxBodySizeMiddleware is
    only a cheap first line of defense before any base64 decoding
    happens).
    """
    import base64
    import binascii

    try:
        data = base64.b64decode(raw_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} is not valid base64: {exc}") from exc

    max_bytes = int(BIOVAULT_MAX_UPLOAD_MB * 1024 * 1024)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} decodes to {len(data):,} bytes, exceeding the maximum allowed size ({BIOVAULT_MAX_UPLOAD_MB} MB).",
        )

    return data
