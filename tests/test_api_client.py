"""
Tests for api/client.py (Phase 23) -- the optional HTTP client layer
for BioVault's backend API.

Runs a real uvicorn server for backend.main:app in a background thread
on a dedicated test port (not the default 8000/8001) for the duration
of this module, then talks to it exactly the way any real caller
(or, eventually, the Streamlit app) would -- over a real HTTP socket,
not an in-process ASGI transport -- to verify the client itself
(URL building, error handling, base64 helpers) works end-to-end.
"""

import threading
import time

import pytest
import uvicorn

from api.client import (
    BioVaultAPIClientError,
    is_backend_available,
    encode,
    decode,
    mutate,
    analyze_storage,
    to_base64,
    from_base64,
)
from backend.main import app as fastapi_app

TEST_PORT = 8765
TEST_BASE_URL = f"http://127.0.0.1:{TEST_PORT}"


@pytest.fixture(scope="module", autouse=True)
def live_backend_server():
    """Start backend.main:app on a dedicated test port for this test
    module only, and tear it down afterward."""
    config = uvicorn.Config(fastapi_app, host="127.0.0.1", port=TEST_PORT, log_level="warning")
    server = uvicorn.Server(config)
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


def test_is_backend_available_true_for_running_server():
    assert is_backend_available(base_url=TEST_BASE_URL) is True


def test_is_backend_available_false_for_unreachable_server():
    assert is_backend_available(base_url="http://127.0.0.1:9", timeout=0.5) is False


def test_to_base64_and_from_base64_round_trip():
    data = b"round trip helper check"
    assert from_base64(to_base64(data)) == data


def test_client_encode_matches_direct_api_call():
    data = b"api client encode test"
    result = encode(to_base64(data), filename="client_test.txt", base_url=TEST_BASE_URL)
    assert result["source_filename"] == "client_test.txt"
    assert result["original_size_bytes"] == len(data)


def test_client_encode_decode_round_trip():
    original = b"api client full round trip payload"
    encode_result = encode(to_base64(original), base_url=TEST_BASE_URL)
    decode_result = decode(encode_result["dna_sequence"], base_url=TEST_BASE_URL)
    recovered = from_base64(decode_result["recovered_bytes_base64"])
    assert recovered == original


def test_client_mutate_calls_real_endpoint():
    encode_result = encode(to_base64(b"mutation client test"), base_url=TEST_BASE_URL)
    result = mutate(encode_result["dna_sequence"], "substitution", 10.0, seed=1, base_url=TEST_BASE_URL)
    assert result["mutation_type"] == "substitution"


def test_client_analyze_storage_calls_real_endpoint():
    result = analyze_storage(100, 400, base_url=TEST_BASE_URL)
    assert result["raw_efficiency_percent"] == 100.0


def test_client_raises_clean_error_on_invalid_input():
    with pytest.raises(BioVaultAPIClientError) as exc_info:
        decode("ACGTX", base_url=TEST_BASE_URL)
    assert exc_info.value.status_code == 400


def test_client_raises_clean_error_when_backend_unreachable():
    with pytest.raises(BioVaultAPIClientError):
        decode("ACGT", base_url="http://127.0.0.1:9", timeout=0.5)
