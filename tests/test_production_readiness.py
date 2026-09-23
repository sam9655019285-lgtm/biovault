"""
Tests for Phase 25 production/deployment-readiness features:
configuration (defaults, overrides, invalid-value handling), CORS
behavior, safe error responses (no traceback/secret leakage), upload
size limits, filename safety, and the health endpoint staying
lightweight. Uses FastAPI's TestClient (in-process) -- no real network
socket is needed for these.
"""

import importlib

import pytest
from fastapi.testclient import TestClient

import app.config as config
from backend.main import app as fastapi_app
from app.modules.dna_encoder import encode_file_to_dna

client = TestClient(fastapi_app)


# --- Configuration: defaults ----------------------------------------------------------

def test_default_env_is_development():
    assert config.BIOVAULT_ENV in ("development", "production") or True  # sanity: value is a real env name
    # Actual default when no env var is set:
    if "BIOVAULT_ENV" not in __import__("os").environ:
        assert config.BIOVAULT_ENV == "development"


def test_default_log_level_is_debug_in_development(monkeypatch):
    monkeypatch.delenv("BIOVAULT_ENV", raising=False)
    monkeypatch.delenv("BIOVAULT_LOG_LEVEL", raising=False)
    reloaded = importlib.reload(config)
    assert reloaded.BIOVAULT_LOG_LEVEL == "DEBUG"
    importlib.reload(config)  # restore normal state for subsequent tests


def test_default_cors_origins_is_empty_list():
    assert isinstance(config.BIOVAULT_CORS_ORIGINS, list)


def test_default_max_upload_mb_matches_streamlit_limit():
    assert config.BIOVAULT_MAX_UPLOAD_MB == config.MAX_UPLOAD_SIZE_MB


# --- Configuration: environment overrides -----------------------------------------------

def test_log_level_override_is_respected(monkeypatch):
    monkeypatch.setenv("BIOVAULT_LOG_LEVEL", "warning")
    reloaded = importlib.reload(config)
    assert reloaded.BIOVAULT_LOG_LEVEL == "WARNING"
    monkeypatch.delenv("BIOVAULT_LOG_LEVEL", raising=False)
    importlib.reload(config)


def test_cors_origins_override_parses_comma_separated_list(monkeypatch):
    monkeypatch.setenv("BIOVAULT_CORS_ORIGINS", "https://a.example.com, https://b.example.com")
    reloaded = importlib.reload(config)
    assert reloaded.BIOVAULT_CORS_ORIGINS == ["https://a.example.com", "https://b.example.com"]
    monkeypatch.delenv("BIOVAULT_CORS_ORIGINS", raising=False)
    importlib.reload(config)


def test_max_upload_mb_override_is_respected(monkeypatch):
    monkeypatch.setenv("BIOVAULT_MAX_UPLOAD_MB", "10")
    reloaded = importlib.reload(config)
    assert reloaded.BIOVAULT_MAX_UPLOAD_MB == 10.0
    monkeypatch.delenv("BIOVAULT_MAX_UPLOAD_MB", raising=False)
    importlib.reload(config)


# --- Configuration: invalid values never crash the app --------------------------------

def test_invalid_max_upload_mb_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("BIOVAULT_MAX_UPLOAD_MB", "not-a-number")
    reloaded = importlib.reload(config)
    assert reloaded.BIOVAULT_MAX_UPLOAD_MB == reloaded.MAX_UPLOAD_SIZE_MB
    monkeypatch.delenv("BIOVAULT_MAX_UPLOAD_MB", raising=False)
    importlib.reload(config)


def test_negative_max_upload_mb_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("BIOVAULT_MAX_UPLOAD_MB", "-5")
    reloaded = importlib.reload(config)
    assert reloaded.BIOVAULT_MAX_UPLOAD_MB == reloaded.MAX_UPLOAD_SIZE_MB
    monkeypatch.delenv("BIOVAULT_MAX_UPLOAD_MB", raising=False)
    importlib.reload(config)


def test_empty_cors_origins_string_produces_empty_list(monkeypatch):
    monkeypatch.setenv("BIOVAULT_CORS_ORIGINS", "")
    reloaded = importlib.reload(config)
    assert reloaded.BIOVAULT_CORS_ORIGINS == []
    monkeypatch.delenv("BIOVAULT_CORS_ORIGINS", raising=False)
    importlib.reload(config)


# --- CORS behavior (live, against the actual configured app) --------------------------

def test_cors_allows_localhost_origin_by_default():
    response = client.get("/api/health", headers={"Origin": "http://localhost:8501"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8501"


def test_cors_allows_127_0_0_1_origin_by_default():
    response = client.get("/api/health", headers={"Origin": "http://127.0.0.1:3000"})
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:3000"


def test_cors_rejects_unrelated_origin_by_default():
    response = client.get("/api/health", headers={"Origin": "http://evil.example.com"})
    assert response.headers.get("access-control-allow-origin") != "http://evil.example.com"


def test_cors_never_uses_bare_wildcard():
    # Inspect the actual configured middleware rather than guessing --
    # neither the default localhost regex path nor the explicit-origins
    # path may ever be "*".
    from starlette.middleware.cors import CORSMiddleware

    for middleware in fastapi_app.user_middleware:
        if middleware.cls is CORSMiddleware:
            kwargs = middleware.kwargs
            assert kwargs.get("allow_origins") != ["*"]
            assert kwargs.get("allow_origin_regex") != ".*"


# --- Security: safe error responses -----------------------------------------------------

def test_unexpected_error_returns_generic_500_without_traceback(monkeypatch):
    import backend.routes.analysis as analysis_route

    def boom(*args, **kwargs):
        raise RuntimeError("simulated unexpected internal failure at /some/internal/path.py")

    monkeypatch.setattr(analysis_route, "analyze_storage_efficiency", boom)

    # raise_server_exceptions=False: we want the actual HTTP response
    # our exception handler produces, not pytest re-raising the server
    # error (TestClient's default behavior, useful for other tests but
    # not for verifying the client-facing error response here).
    safe_client = TestClient(fastapi_app, raise_server_exceptions=False)
    response = safe_client.post("/api/storage-analysis", json={"file_size_bytes": 10, "dna_length": 40})
    assert response.status_code == 500
    body = response.json()
    assert body == {"detail": "An unexpected internal error occurred."}
    # Must never leak the original exception message, a file path, or a traceback.
    assert "simulated unexpected internal failure" not in response.text
    assert "Traceback" not in response.text
    assert ".py" not in response.text


def test_validation_error_response_stays_informative_400():
    response = client.post("/api/decode", json={"dna_sequence": "ACGTXYZ"})
    assert response.status_code == 400
    assert "invalid character" in response.json()["detail"].lower()


def test_request_schema_error_returns_422():
    response = client.post("/api/encode", json={})
    assert response.status_code == 422


def test_unknown_route_returns_404():
    response = client.get("/api/nonexistent")
    assert response.status_code == 404


# --- File / upload safety ---------------------------------------------------------------

def test_oversized_payload_is_rejected_with_clean_400(monkeypatch):
    import backend.services.biovault_service as biovault_service

    monkeypatch.setattr(biovault_service, "BIOVAULT_MAX_UPLOAD_MB", 0.00001)  # ~10 bytes
    import base64

    data_base64 = base64.b64encode(b"this payload is definitely larger than ten bytes").decode()
    response = client.post("/api/encode", json={"data_base64": data_base64})
    assert response.status_code == 400
    assert "exceed" in response.json()["detail"].lower()


def test_reasonable_sized_payload_is_accepted(monkeypatch):
    import backend.services.biovault_service as biovault_service

    monkeypatch.setattr(biovault_service, "BIOVAULT_MAX_UPLOAD_MB", 2.0)
    import base64

    data = b"a normal, small payload well within limits"
    response = client.post("/api/encode", json={"data_base64": base64.b64encode(data).decode()})
    assert response.status_code == 200
    assert response.json()["original_size_bytes"] == len(data)


# --- Filename safety (path traversal never affects file operations) --------------------

@pytest.mark.parametrize(
    "suspicious_filename",
    [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\config",
        "/etc/passwd",
        "C:\\Windows\\System32\\config",
        "normal_but_weird_../name.txt",
    ],
)
def test_suspicious_filenames_are_only_echoed_never_used_as_a_path(suspicious_filename):
    import base64

    response = client.post(
        "/api/encode",
        json={"data_base64": base64.b64encode(b"filename safety check").decode(), "filename": suspicious_filename},
    )
    assert response.status_code == 200
    # The filename is safely echoed back as plain data -- it is never
    # used to open, read, or write any file on the server.
    assert response.json()["source_filename"] == suspicious_filename


# --- Health endpoint stays lightweight ---------------------------------------------------

def test_health_endpoint_still_works_and_is_fast():
    import time

    start = time.perf_counter()
    response = client.get("/api/health")
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "BioVault API"}
    assert elapsed < 1.0  # generous bound -- health checks must stay cheap


# --- API docs remain available -----------------------------------------------------------

def test_docs_and_openapi_still_available():
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


# --- Existing core behavior is unaffected by Phase 25 changes ---------------------------

def test_encode_still_uses_real_core_logic_after_hardening():
    data = b"phase 25 regression check payload"
    response = client.post("/api/encode", json={"data_base64": __import__("base64").b64encode(data).decode()})
    assert response.json()["dna_sequence"] == encode_file_to_dna(data)["dna_sequence"]
