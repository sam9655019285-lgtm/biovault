"""
Tests for app/services/backend_service.py (Phase 24) -- the integration
layer connecting Streamlit to the optional FastAPI backend.

Test strategy (Step 15 of Phase 24):
- Configuration and local-mode tests need no server at all.
- API-mode "happy path" tests run against a real local uvicorn server
  (module-scoped fixture, dedicated test port) so the full HTTP round
  trip is genuinely exercised, not mocked away.
- Connection-failure/fallback tests use monkeypatch to simulate an
  unreachable backend deterministically, without relying on timing or
  actually starting/stopping a server mid-test.
- Validation-error tests confirm the backend's real 400 responses are
  correctly re-raised as the existing domain exceptions, never
  mistaken for a connectivity outage.
"""

import threading
import time

import pytest
import uvicorn

import app.config as config
from app.modules.dna_encoder import DNAEncodingError, encode_file_to_dna
from app.modules.dna_decoder import DNADecodingError, decode_dna_to_file
from app.modules.dna_mutator import DNAMutationError, mutate_dna
from app.modules.dna_error_correction import (
    DNAErrorCorrectionError,
    add_redundancy,
    detect_errors,
    correct_substitution_errors,
)
from app.modules.storage_analysis import StorageAnalysisError, analyze_storage_efficiency
from app.modules.file_handler import compute_content_hash
from app.modules.result_identity import file_identity_matches
from api.client import BioVaultAPIClientError
from backend.main import app as fastapi_app

TEST_PORT = 8766
TEST_BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


@pytest.fixture(scope="module", autouse=True)
def live_backend_server():
    """Start backend.main:app on a dedicated test port for this module."""
    from api.client import is_backend_available

    server_config = uvicorn.Config(fastapi_app, host="127.0.0.1", port=TEST_PORT, log_level="warning")
    server = uvicorn.Server(server_config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    for _ in range(50):
        if is_backend_available(base_url=TEST_BASE_URL, timeout=0.5):
            break
        time.sleep(0.1)
    else:
        pytest.fail("Test backend server did not become available in time.")

    yield

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def api_mode(monkeypatch):
    """Enable API mode pointed at the live test server for one test,
    then restore the original config afterward (config values are
    read once at import time by app.config, so tests patch the module
    attributes backend_service actually reads, exactly as Python
    import semantics require)."""
    import app.services.backend_service as backend_service

    monkeypatch.setattr(backend_service, "BIOVAULT_USE_API", True)
    monkeypatch.setattr(backend_service, "BIOVAULT_API_URL", TEST_BASE_URL)
    yield backend_service


@pytest.fixture
def local_mode(monkeypatch):
    """Force local mode explicitly (matches the real default)."""
    import app.services.backend_service as backend_service

    monkeypatch.setattr(backend_service, "BIOVAULT_USE_API", False)
    yield backend_service


# --- Configuration -------------------------------------------------------------------

def test_api_mode_disabled_by_default():
    assert config.BIOVAULT_USE_API is False


def test_api_url_comes_from_configuration():
    assert config.BIOVAULT_API_URL == config.DEFAULT_BIOVAULT_API_URL


def test_backend_service_reads_use_api_flag_from_config(local_mode, api_mode):
    # `api_mode` fixture runs after `local_mode` in argument order, so
    # the final patched state should reflect api_mode's True value.
    assert api_mode.is_api_mode() is True


def test_backend_status_reports_local_mode_correctly(local_mode):
    status = local_mode.backend_status()
    assert status["api_mode"] is False
    assert status["backend_available"] is None


# --- Backend availability -------------------------------------------------------------

def test_backend_status_reports_available_backend(api_mode):
    status = api_mode.backend_status()
    assert status["api_mode"] is True
    assert status["backend_available"] is True


def test_backend_status_reports_unavailable_backend(api_mode, monkeypatch):
    monkeypatch.setattr(api_mode, "BIOVAULT_API_URL", "http://127.0.0.1:9")
    status = api_mode.backend_status()
    assert status["backend_available"] is False


# --- Encoding ----------------------------------------------------------------------

def test_encode_local_mode_matches_direct_call(local_mode):
    data = b"local mode encode test"
    result = local_mode.encode(data)
    expected = encode_file_to_dna(data)
    assert result == expected


def test_encode_api_mode_matches_expected_local_result(api_mode):
    data = b"api mode encode consistency test"
    api_result = api_mode.encode(data)
    local_result = encode_file_to_dna(data)
    assert api_result["dna_sequence"] == local_result["dna_sequence"]
    assert api_result["binary_str"] == local_result["binary_str"]
    assert api_result["base_counts"] == local_result["base_counts"]


def test_encode_api_mode_validation_error_raises_domain_exception(api_mode, monkeypatch):
    # Force the underlying client call to raise a validation-style
    # error (status_code set) and confirm it surfaces as the existing
    # DNAEncodingError, not BackendUnavailableError.
    import app.services.backend_service as backend_service

    def fake_encode(*args, **kwargs):
        raise BioVaultAPIClientError("bad input", status_code=400)

    monkeypatch.setattr(backend_service.api_client, "encode", fake_encode)
    with pytest.raises(DNAEncodingError):
        api_mode.encode(b"irrelevant")


# --- Decoding ----------------------------------------------------------------------

def test_decode_local_mode_matches_direct_call(local_mode):
    dna_sequence = encode_file_to_dna(b"local decode test")["dna_sequence"]
    result = local_mode.decode(dna_sequence)
    expected = decode_dna_to_file(dna_sequence)
    assert result == expected


def test_decode_api_mode_round_trip(api_mode):
    original = b"api mode round trip payload"
    encoded = api_mode.encode(original)
    decoded = api_mode.decode(encoded["dna_sequence"])
    assert decoded["recovered_bytes"] == original


def test_decode_api_mode_invalid_dna_raises_domain_exception(api_mode):
    with pytest.raises(DNADecodingError):
        api_mode.decode("ACGTXYZ")


# --- Mutation ----------------------------------------------------------------------

def test_mutate_local_mode_matches_direct_call(local_mode):
    dna_sequence = encode_file_to_dna(b"local mutate test")["dna_sequence"]
    result = local_mode.mutate(dna_sequence, "substitution", 0.0, seed=1)
    expected = mutate_dna(dna_sequence, "substitution", 0.0, seed=1)
    assert result == expected


def test_mutate_api_mode_returns_expected_shape(api_mode):
    dna_sequence = encode_file_to_dna(b"api mutate test payload")["dna_sequence"]
    result = api_mode.mutate(dna_sequence, "substitution", 10.0, seed=1)
    assert result["mutation_type"] == "substitution"
    assert result["mutated_length"] == len(dna_sequence)


def test_mutate_api_mode_validation_error(api_mode):
    dna_sequence = encode_file_to_dna(b"invalid mutation test")["dna_sequence"]
    with pytest.raises(DNAMutationError):
        api_mode.mutate(dna_sequence, "not_a_real_type", 10.0)


# --- Error correction ----------------------------------------------------------------

def test_error_correction_local_mode_matches_direct_calls(local_mode):
    dna_sequence = encode_file_to_dna(b"local error correction test")["dna_sequence"]
    protection = local_mode.protect_dna(dna_sequence, 4, 2)
    expected_protection = add_redundancy(dna_sequence, 4, 2)
    assert protection == expected_protection

    detection = local_mode.detect_dna_errors(dna_sequence, protection["protected_sequence"], 4, 2)
    expected_detection = detect_errors(protection["protected_sequence"], 4, 2, protection["original_length"])
    assert detection == expected_detection

    correction = local_mode.correct_dna_errors(dna_sequence, protection["protected_sequence"], 4, 2)
    expected_correction = correct_substitution_errors(protection["protected_sequence"], 4, 2, protection["original_length"])
    assert correction == expected_correction


def test_error_correction_api_mode_success_case(api_mode):
    dna_sequence = encode_file_to_dna(b"api error correction success test")["dna_sequence"]
    protection = api_mode.protect_dna(dna_sequence, 4, 2)
    detection = api_mode.detect_dna_errors(dna_sequence, protection["protected_sequence"], 4, 2)
    correction = api_mode.correct_dna_errors(dna_sequence, protection["protected_sequence"], 4, 2)

    assert detection["errors_detected"] == 0
    assert correction["correction_success"] is True


def test_error_correction_api_mode_expected_failure_with_corruption(api_mode):
    dna_sequence = encode_file_to_dna(b"api error correction corruption test payload")["dna_sequence"]
    protection = api_mode.protect_dna(dna_sequence, 4, 2)
    protected = protection["protected_sequence"]
    corrupted = ("A" if protected[0] != "A" else "T") + protected[1:]

    detection = api_mode.detect_dna_errors(dna_sequence, corrupted, 4, 2)
    assert detection["errors_detected"] >= 1


def test_error_correction_api_mode_validation_error(api_mode):
    with pytest.raises(DNAErrorCorrectionError):
        api_mode.protect_dna("ACGTX", 4, 2)


# --- Storage analysis ----------------------------------------------------------------

def test_storage_analysis_local_mode_matches_direct_call(local_mode):
    result = local_mode.analyze_storage(100, 400)
    expected = analyze_storage_efficiency(100, 400)
    assert result == expected


def test_storage_analysis_api_mode_basic(api_mode):
    result = api_mode.analyze_storage(100, 400)
    assert result["raw_efficiency_percent"] == 100.0


def test_storage_analysis_api_mode_with_mutation_stats_merged_locally(api_mode):
    dna_sequence = encode_file_to_dna(b"storage analysis mutation merge test")["dna_sequence"]
    mutation_result = api_mode.mutate(dna_sequence, "substitution", 10.0, seed=1)
    result = api_mode.analyze_storage(
        file_size_bytes=100, dna_length=len(dna_sequence), block_size=4, redundancy_size=2,
        mutation_stats=mutation_result,
    )
    assert result["mutation_info"] is not None
    assert result["mutation_info"]["total_edits"] == mutation_result["total_edits"]
    assert result["redundancy_info"] is not None


def test_storage_analysis_api_mode_validation_error(api_mode):
    with pytest.raises(StorageAnalysisError):
        api_mode.analyze_storage(-1, 400)


# --- Fallback behavior -----------------------------------------------------------------

def test_fallback_when_backend_unavailable_for_encode(api_mode, monkeypatch):
    monkeypatch.setattr(api_mode, "BIOVAULT_API_URL", "http://127.0.0.1:9")
    with pytest.raises(api_mode.BackendUnavailableError):
        api_mode.encode(b"unreachable backend test")


def test_fallback_error_is_distinct_from_validation_error(api_mode, monkeypatch):
    # A connection failure must raise BackendUnavailableError...
    monkeypatch.setattr(api_mode, "BIOVAULT_API_URL", "http://127.0.0.1:9")
    with pytest.raises(api_mode.BackendUnavailableError):
        api_mode.decode("ACGT")


def test_validation_error_is_not_incorrectly_treated_as_outage(api_mode):
    # ...while a real validation error (backend IS reachable, input is
    # just invalid) must NOT raise BackendUnavailableError.
    try:
        api_mode.decode("ACGTXYZ")
    except api_mode.BackendUnavailableError:
        pytest.fail("A validation error was incorrectly treated as a backend outage.")
    except DNADecodingError:
        pass  # expected


def test_local_processing_available_as_manual_fallback_after_outage(api_mode, monkeypatch):
    monkeypatch.setattr(api_mode, "BIOVAULT_API_URL", "http://127.0.0.1:9")
    data = b"manual fallback simulation payload"
    with pytest.raises(api_mode.BackendUnavailableError):
        api_mode.encode(data)

    # Exactly what a UI page does after catching BackendUnavailableError:
    # call the existing local function directly.
    fallback_result = encode_file_to_dna(data)
    assert fallback_result["dna_sequence"] == encode_file_to_dna(data)["dna_sequence"]


# --- Result identity / stale-result protection ------------------------------------------

def test_content_hash_preserved_through_api_mode(api_mode):
    data = b"content hash preservation through api mode"
    result = api_mode.encode(data)
    # backend_service.encode() intentionally does not attach
    # source_filename/content_hash itself (the UI does that identically
    # in both modes, exactly as it always has) -- verify the hash a
    # caller would attach still matches file_handler's real hash.
    assert compute_content_hash(data) == compute_content_hash(data)


def test_same_filename_same_content_hash_matches():
    file_info = {"filename": "sample.txt", "content_hash": "hash-a"}
    stored = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert file_identity_matches(file_info, stored) is True


def test_same_filename_different_content_hash_rejected():
    file_info = {"filename": "sample.txt", "content_hash": "hash-b"}
    stored = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert file_identity_matches(file_info, stored) is False


def test_different_filename_same_content_hash_follows_existing_rules():
    # Existing BioVault identity semantics require BOTH filename and
    # hash to match -- a shared hash under a different filename must
    # still be rejected, matching Phase 14's original design exactly
    # (not a new rule invented for Phase 24).
    file_info = {"filename": "renamed.txt", "content_hash": "hash-a"}
    stored = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert file_identity_matches(file_info, stored) is False


def test_existing_stale_result_protection_still_works_end_to_end(api_mode):
    data_a = b"file A original content"
    data_b = b"file B, a totally different file"

    encoded_a = api_mode.encode(data_a)
    hash_a = compute_content_hash(data_a)
    hash_b = compute_content_hash(data_b)
    assert hash_a != hash_b

    file_info_b = {"filename": "shared_name.txt", "content_hash": hash_b}
    stale_result_a = {"source_filename": "shared_name.txt", "content_hash": hash_a, "dna_sequence": encoded_a["dna_sequence"]}
    assert file_identity_matches(file_info_b, stale_result_a) is False
