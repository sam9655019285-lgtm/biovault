"""
Optional HTTP client for BioVault's backend API (backend/main.py).

This is a THIN, OPTIONAL layer: nothing in the existing Streamlit UI is
required to use it, and no existing page has been changed to depend on
it. Its purpose is to let the Streamlit app (or any other script) call
the backend over HTTP once/if that becomes desirable, while every
existing page keeps working exactly as before by calling
app/modules/*.py directly and locally.

The backend base URL comes from app.config.BIOVAULT_API_URL (itself
driven by the BIOVAULT_API_URL environment variable, default
http://127.0.0.1:8000) -- never hard-coded here or anywhere else.
"""

from typing import Optional

import httpx

from app.config import BIOVAULT_API_URL

DEFAULT_TIMEOUT_SECONDS = 10.0


class BioVaultAPIClientError(Exception):
    """Raised when a backend API call fails (network error or a non-2xx
    response). Carries the HTTP status code when one was received."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _post(path: str, json_body: dict, base_url: str, timeout: float) -> dict:
    try:
        response = httpx.post(f"{base_url}{path}", json=json_body, timeout=timeout)
    except httpx.HTTPError as exc:
        raise BioVaultAPIClientError(f"Could not reach BioVault API at {base_url}{path}: {exc}") from exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise BioVaultAPIClientError(detail, status_code=response.status_code)

    return response.json()


def is_backend_available(base_url: str = BIOVAULT_API_URL, timeout: float = 2.0) -> bool:
    """Return True only if the backend's /api/health endpoint responds
    successfully -- safe to call before deciding whether to use the API
    at all."""
    try:
        response = httpx.get(f"{base_url}/api/health", timeout=timeout)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def encode(
    data_base64: str,
    filename: Optional[str] = None,
    base_url: str = BIOVAULT_API_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Call POST /api/encode. `data_base64` must already be a base64
    string (see api.client.to_base64())."""
    return _post("/api/encode", {"data_base64": data_base64, "filename": filename}, base_url, timeout)


def decode(dna_sequence: str, base_url: str = BIOVAULT_API_URL, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict:
    """Call POST /api/decode."""
    return _post("/api/decode", {"dna_sequence": dna_sequence}, base_url, timeout)


def mutate(
    dna_sequence: str,
    mutation_type: str,
    mutation_rate: float,
    seed: Optional[int] = None,
    base_url: str = BIOVAULT_API_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Call POST /api/mutation."""
    return _post(
        "/api/mutation",
        {"dna_sequence": dna_sequence, "mutation_type": mutation_type, "mutation_rate": mutation_rate, "seed": seed},
        base_url,
        timeout,
    )


def correct_errors(
    dna_sequence: str,
    received_sequence: Optional[str] = None,
    block_size: int = 4,
    redundancy_size: int = 2,
    base_url: str = BIOVAULT_API_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Call POST /api/error-correction."""
    return _post(
        "/api/error-correction",
        {
            "dna_sequence": dna_sequence,
            "received_sequence": received_sequence,
            "block_size": block_size,
            "redundancy_size": redundancy_size,
        },
        base_url,
        timeout,
    )


def analyze_storage(
    file_size_bytes: int,
    dna_length: int,
    block_size: Optional[int] = None,
    redundancy_size: Optional[int] = None,
    base_url: str = BIOVAULT_API_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Call POST /api/storage-analysis."""
    return _post(
        "/api/storage-analysis",
        {
            "file_size_bytes": file_size_bytes,
            "dna_length": dna_length,
            "block_size": block_size,
            "redundancy_size": redundancy_size,
        },
        base_url,
        timeout,
    )


def to_base64(data: bytes) -> str:
    """Convenience helper: encode raw bytes into the base64 string the
    /api/encode endpoint expects."""
    import base64

    return base64.b64encode(data).decode("ascii")


def from_base64(data_base64: str) -> bytes:
    """Convenience helper: decode a base64 string (e.g. from
    /api/decode's recovered_bytes_base64) back into raw bytes."""
    import base64

    return base64.b64decode(data_base64)
