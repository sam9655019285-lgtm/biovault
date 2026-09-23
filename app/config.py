"""
Project-wide constants and settings for BioVault.

Keeping these values in one place means every module (UI, encoding,
mutation simulation, etc.) refers to the same source of truth instead
of hard-coding numbers/strings in multiple files.
"""

import os

APP_TITLE = "BioVault"
APP_SUBTITLE = "DNA Digital Data Storage and Error Simulation Platform"
APP_ICON = "🧬"

# Streamlit's set_page_config() call must happen once, so we centralize
# the arguments here and import them from the main entry point.
PAGE_CONFIG = {
    "page_title": APP_TITLE,
    "page_icon": APP_ICON,
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# Educational disclaimer shown throughout the app. DNA storage here is
# simulated entirely in software -- no wet-lab / biological process is
# performed.
DISCLAIMER = (
    "BioVault is an educational **simulation**. It does not perform real "
    "DNA synthesis, sequencing, genetic engineering, or any laboratory "
    "procedure. All 'DNA' in this app is a text representation (A/T/G/C "
    "characters) used to demonstrate the *concept* of DNA-based digital "
    "data storage."
)

# Reasonable upload limit for the prototype (kept small since each byte
# expands into 4 DNA bases during encoding).
MAX_UPLOAD_SIZE_MB = 2

# The four DNA nucleotide bases used throughout the app.
DNA_BASES = ("A", "T", "G", "C")

# Phase 23: base URL for the optional backend API (backend/main.py).
# Overridable via the BIOVAULT_API_URL environment variable so the
# Streamlit app, the API client (api/client.py), and any test/deploy
# script all agree on one address instead of hard-coding it separately
# in multiple places. The Streamlit UI does not depend on the backend
# being reachable -- it continues to call the same app/modules/*.py
# functions directly; this URL is only used by api/client.py and by
# anyone choosing to call the backend instead.
DEFAULT_BIOVAULT_API_URL = "http://127.0.0.1:8000"
BIOVAULT_API_URL = os.environ.get("BIOVAULT_API_URL", DEFAULT_BIOVAULT_API_URL)

# Phase 24: whether Streamlit should route core operations (encode,
# decode, mutate, error-correct, analyze storage) through the backend
# API instead of calling app/modules/*.py directly. Defaults to False
# so the existing, already-verified direct/local behavior remains the
# safe default -- API mode is strictly opt-in via the BIOVAULT_USE_API
# environment variable ("true"/"1"/"yes", case-insensitive).
_TRUTHY_VALUES = {"true", "1", "yes", "on"}
BIOVAULT_USE_API = os.environ.get("BIOVAULT_USE_API", "false").strip().lower() in _TRUTHY_VALUES

# --- Phase 25: production/deployment configuration -----------------------------

# Which environment this process is running in. Only used to pick a
# sensible logging default and to label the running service -- it never
# changes any DNA/encoding behavior. "development" keeps local defaults
# convenient; set to "production" via the BIOVAULT_ENV environment
# variable in a real deployment.
BIOVAULT_ENV = os.environ.get("BIOVAULT_ENV", "development").strip().lower()

# Python logging level name for the backend (see backend/main.py).
# Overridable via BIOVAULT_LOG_LEVEL so a deployment can turn logging
# up or down without editing code. Defaults to INFO in production and
# DEBUG in development for a more informative local dev experience.
_DEFAULT_LOG_LEVEL = "DEBUG" if BIOVAULT_ENV != "production" else "INFO"
BIOVAULT_LOG_LEVEL = os.environ.get("BIOVAULT_LOG_LEVEL", _DEFAULT_LOG_LEVEL).strip().upper()

# Comma-separated list of additional allowed CORS origins for the
# backend API, e.g. "https://my-frontend.example.com,https://admin.example.com".
# When unset (the default), the backend keeps its existing, safe
# localhost-only origin pattern (see backend/main.py) -- this variable
# only ever ADDS explicitly-listed origins for a real deployment; it
# never enables a bare wildcard ("*").
BIOVAULT_CORS_ORIGINS = [
    origin.strip() for origin in os.environ.get("BIOVAULT_CORS_ORIGINS", "").split(",") if origin.strip()
]

def _parse_positive_float(raw_value, default: float) -> float:
    """Parse an environment variable as a positive float, falling back
    to `default` (rather than crashing the whole application at import
    time) for anything missing, non-numeric, or non-positive."""
    if raw_value is None:
        return default
    try:
        parsed = float(raw_value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


# Maximum size (in megabytes) of a single file the backend's /api/encode
# endpoint will accept, mirroring the same spirit as MAX_UPLOAD_SIZE_MB
# above for the Streamlit uploader. The backend is a separate process
# (and can be a separate deployment) with no built-in request-size
# limit of its own, so this closes that gap. Overridable via
# BIOVAULT_MAX_UPLOAD_MB; an invalid value safely falls back to the
# default rather than crashing the application at startup.
BIOVAULT_MAX_UPLOAD_MB = _parse_positive_float(os.environ.get("BIOVAULT_MAX_UPLOAD_MB"), MAX_UPLOAD_SIZE_MB)
