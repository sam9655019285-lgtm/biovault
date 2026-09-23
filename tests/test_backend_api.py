"""
Tests for the Phase 23 backend API (backend/main.py and routes).

Uses FastAPI's TestClient (in-process, no real network/socket needed)
to verify every endpoint calls BioVault's existing core logic correctly,
returns proper HTTP status codes for valid/invalid input, and never
duplicates the underlying algorithms. Also verifies encode/decode
round-trip compatibility and content-hash/identity behavior.
"""

import base64

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from app.modules.dna_encoder import encode_file_to_dna
from app.modules.file_handler import compute_content_hash
from app.modules.result_identity import file_identity_matches

client = TestClient(app)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


# --- Health ----------------------------------------------------------------------

def test_health_returns_200():
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_returns_correct_status_response():
    response = client.get("/api/health")
    body = response.json()
    assert body == {"status": "ok", "service": "BioVault API"}


# --- Encoding ----------------------------------------------------------------------

def test_encode_valid_request_returns_200():
    response = client.post("/api/encode", json={"data_base64": _b64(b"Hello, BioVault!")})
    assert response.status_code == 200


def test_encode_uses_existing_encoding_logic():
    data = b"API must reuse the real encoder, not a second implementation."
    response = client.post("/api/encode", json={"data_base64": _b64(data)})
    body = response.json()
    real_result = encode_file_to_dna(data)
    assert body["dna_sequence"] == real_result["dna_sequence"]
    assert body["dna_length"] == real_result["dna_length"]
    assert body["base_counts"] == real_result["base_counts"]


def test_encode_invalid_base64_returns_400():
    response = client.post("/api/encode", json={"data_base64": "not-valid-base64!!"})
    assert response.status_code == 400


def test_encode_missing_field_returns_422():
    response = client.post("/api/encode", json={})
    assert response.status_code == 422


def test_encode_includes_content_hash_matching_file_handler():
    data = b"content hash consistency check"
    response = client.post("/api/encode", json={"data_base64": _b64(data), "filename": "sample.txt"})
    body = response.json()
    assert body["content_hash"] == compute_content_hash(data)
    assert body["source_filename"] == "sample.txt"


# --- Decoding ----------------------------------------------------------------------

def test_decode_valid_dna_returns_200():
    dna_sequence = encode_file_to_dna(b"decode test")["dna_sequence"]
    response = client.post("/api/decode", json={"dna_sequence": dna_sequence})
    assert response.status_code == 200


def test_decode_invalid_dna_characters_returns_400():
    response = client.post("/api/decode", json={"dna_sequence": "ACGTXYZ"})
    assert response.status_code == 400
    assert "invalid character" in response.json()["detail"].lower()


def test_decode_empty_dna_returns_400():
    response = client.post("/api/decode", json={"dna_sequence": ""})
    assert response.status_code == 400


def test_encode_decode_round_trip_via_api():
    original = b"BioVault Phase 23 API round-trip verification payload."
    encode_response = client.post("/api/encode", json={"data_base64": _b64(original)})
    dna_sequence = encode_response.json()["dna_sequence"]

    decode_response = client.post("/api/decode", json={"dna_sequence": dna_sequence})
    recovered = base64.b64decode(decode_response.json()["recovered_bytes_base64"])

    assert recovered == original


# --- Mutation ----------------------------------------------------------------------

def test_mutation_valid_request_returns_200():
    dna_sequence = encode_file_to_dna(b"mutation test payload")["dna_sequence"]
    response = client.post(
        "/api/mutation",
        json={"dna_sequence": dna_sequence, "mutation_type": "substitution", "mutation_rate": 10.0, "seed": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mutation_type"] == "substitution"
    assert body["mutated_length"] == len(dna_sequence)


def test_mutation_zero_rate_leaves_sequence_unchanged():
    dna_sequence = encode_file_to_dna(b"zero rate mutation test")["dna_sequence"]
    response = client.post(
        "/api/mutation",
        json={"dna_sequence": dna_sequence, "mutation_type": "substitution", "mutation_rate": 0.0, "seed": 1},
    )
    body = response.json()
    assert body["mutated_sequence"] == dna_sequence
    assert body["total_edits"] == 0


def test_mutation_invalid_type_returns_400():
    dna_sequence = encode_file_to_dna(b"invalid mutation type test")["dna_sequence"]
    response = client.post(
        "/api/mutation",
        json={"dna_sequence": dna_sequence, "mutation_type": "not_a_type", "mutation_rate": 10.0},
    )
    assert response.status_code == 400


def test_mutation_invalid_rate_returns_422():
    dna_sequence = encode_file_to_dna(b"invalid rate test")["dna_sequence"]
    response = client.post(
        "/api/mutation",
        json={"dna_sequence": dna_sequence, "mutation_type": "substitution", "mutation_rate": 150.0},
    )
    assert response.status_code == 422


# --- Error correction ----------------------------------------------------------------

def test_error_correction_successful_case_returns_200():
    dna_sequence = encode_file_to_dna(b"error correction success test")["dna_sequence"]
    response = client.post("/api/error-correction", json={"dna_sequence": dna_sequence})
    assert response.status_code == 200
    body = response.json()
    assert body["correction"]["errors_detected"] == 0
    assert body["correction"]["correction_success"] is True


def test_error_correction_with_corrupted_received_sequence():
    dna_sequence = encode_file_to_dna(b"error correction corruption test payload")["dna_sequence"]
    protect_response = client.post("/api/error-correction", json={"dna_sequence": dna_sequence})
    protected = protect_response.json()["protected_sequence"]

    # Corrupt exactly one base in the first block.
    corrupted = ("A" if protected[0] != "A" else "T") + protected[1:]
    response = client.post(
        "/api/error-correction",
        json={"dna_sequence": dna_sequence, "received_sequence": corrupted},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["detection"]["errors_detected"] >= 1


def test_error_correction_invalid_dna_returns_400():
    response = client.post("/api/error-correction", json={"dna_sequence": "ACGTX"})
    assert response.status_code == 400


def test_error_correction_expected_failure_length_mismatch():
    dna_sequence = encode_file_to_dna(b"length mismatch failure test payload")["dna_sequence"]
    protect_response = client.post("/api/error-correction", json={"dna_sequence": dna_sequence})
    protected = protect_response.json()["protected_sequence"]
    truncated = protected[:-1]

    response = client.post(
        "/api/error-correction",
        json={"dna_sequence": dna_sequence, "received_sequence": truncated},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["detection"]["length_matches_expected"] is False
    assert body["detection"]["errors_detected"] is None


# --- Storage analysis ----------------------------------------------------------------

def test_storage_analysis_valid_calculation_returns_200():
    response = client.post("/api/storage-analysis", json={"file_size_bytes": 100, "dna_length": 400})
    assert response.status_code == 200
    body = response.json()
    assert body["raw_efficiency_percent"] == 100.0


def test_storage_analysis_with_redundancy_settings():
    response = client.post(
        "/api/storage-analysis",
        json={"file_size_bytes": 100, "dna_length": 400, "block_size": 4, "redundancy_size": 2},
    )
    body = response.json()
    assert body["redundancy_info"] is not None
    assert body["redundancy_info"]["num_blocks"] == 100


def test_storage_analysis_invalid_negative_input_returns_422():
    response = client.post("/api/storage-analysis", json={"file_size_bytes": -1, "dna_length": 400})
    assert response.status_code == 422


# --- Hash / identity behavior ----------------------------------------------------------

def test_content_hash_is_preserved_across_the_api():
    data = b"identity preservation check"
    response = client.post("/api/encode", json={"data_base64": _b64(data), "filename": "a.txt"})
    body = response.json()
    assert body["content_hash"] == compute_content_hash(data)


def test_same_filename_different_content_does_not_incorrectly_match():
    response_a = client.post("/api/encode", json={"data_base64": _b64(b"content A"), "filename": "same.txt"})
    response_b = client.post("/api/encode", json={"data_base64": _b64(b"content B, totally different"), "filename": "same.txt"})

    hash_a = response_a.json()["content_hash"]
    hash_b = response_b.json()["content_hash"]
    assert hash_a != hash_b

    file_info_b = {"filename": "same.txt", "content_hash": hash_b}
    stale_result_a = {"source_filename": "same.txt", "content_hash": hash_a}
    assert file_identity_matches(file_info_b, stale_result_a) is False


# --- 404 -------------------------------------------------------------------------------

def test_unknown_route_returns_404():
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404


# --- API documentation availability -----------------------------------------------------

def test_docs_endpoint_available():
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema_available():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()
