"""
BioVault backend API -- entry point.

Run with:  uvicorn backend.main:app --reload          (development)
Run with:  uvicorn backend.main:app --host 0.0.0.0 --port 8000   (deployment)

This exposes BioVault's EXISTING, already-tested core modules
(app/modules/*.py) over a small FastAPI HTTP layer, so the same
encoding/decoding/mutation/error-correction/storage-analysis logic the
Streamlit UI already uses can also be called by other clients (a
future frontend, scripts, automated tests). No algorithm is
reimplemented here -- every route is a thin wrapper that calls the real
function directly.

EDUCATIONAL SOFTWARE SIMULATION ONLY -- same disclaimer as the rest of
BioVault: this does not perform real DNA synthesis, sequencing, or
laboratory storage.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import BIOVAULT_CORS_ORIGINS, BIOVAULT_ENV, BIOVAULT_LOG_LEVEL, BIOVAULT_MAX_UPLOAD_MB
from backend.routes import health, encoding, decoding, mutation, error_correction, analysis

logger = logging.getLogger("biovault.backend")

# Phase 25: configurable log level, set once here rather than scattered
# across modules. `force=False` (the default) means this is a no-op if
# something else (e.g. uvicorn's own CLI logging setup, or pytest) has
# already configured the root logger -- it only takes effect when this
# module is the first thing to configure logging.
logging.basicConfig(
    level=getattr(logging, BIOVAULT_LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# IMPORTANT: never log uploaded file contents, DNA sequences, or other
# request payload data -- only operational events (startup/shutdown,
# which route failed, that an error occurred) are logged anywhere in
# this backend. See individual route modules: none of them log request
# bodies.


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("BioVault API starting up (env=%s, log_level=%s)", BIOVAULT_ENV, BIOVAULT_LOG_LEVEL)
    yield
    logger.info("BioVault API shutting down")


app = FastAPI(
    title="BioVault API",
    description=(
        "HTTP API for BioVault's DNA data-storage simulation core. "
        "Educational software simulation only -- not real DNA synthesis, "
        "sequencing, or laboratory storage."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose declared Content-Length exceeds
    BIOVAULT_MAX_UPLOAD_MB, before any route handler (and therefore
    before any base64 decoding) runs. This is a defense-in-depth check
    -- routes that accept a data payload also validate the actual
    decoded size themselves (see backend/services/biovault_service.py).
    A missing/absent Content-Length header (e.g. chunked requests) is
    allowed through here; the route-level check still applies once the
    body is read.
    """

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": f"Request body exceeds the maximum allowed size ({BIOVAULT_MAX_UPLOAD_MB} MB)."},
                    )
            except ValueError:
                pass  # malformed header -- let normal request handling deal with it
        return await call_next(request)


app.add_middleware(MaxBodySizeMiddleware, max_bytes=int(BIOVAULT_MAX_UPLOAD_MB * 1024 * 1024))

# CORS: BIOVAULT_CORS_ORIGINS (comma-separated) lets a real deployment
# explicitly allow additional origins (e.g. a deployed frontend) without
# ever falling back to a bare wildcard. When unset (the default), the
# original development-friendly localhost/127.0.0.1 pattern is used
# unchanged -- this preserves exact Phase 23 behavior for anyone not
# using the new variable.
if BIOVAULT_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=BIOVAULT_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(encoding.router, prefix="/api", tags=["encoding"])
app.include_router(decoding.router, prefix="/api", tags=["decoding"])
app.include_router(mutation.router, prefix="/api", tags=["mutation"])
app.include_router(error_correction.router, prefix="/api", tags=["error-correction"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch anything not already turned into a clean HTTPException by
    a route (see backend/services/biovault_service.py) and return a
    generic 500 -- never a raw Python traceback, file path, or other
    internal detail. The exception itself IS logged server-side (for
    operators to diagnose), but the request payload is not."""
    logger.exception("Unhandled error while processing %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected internal error occurred."})
