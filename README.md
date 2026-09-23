# BioVault – DNA Digital Data Storage and Error Simulation Platform

An educational Streamlit app that simulates encoding digital files into DNA
base sequences (A/T/G/C), introduces simulated mutations/errors, attempts a
simplified error-correction pass, and decodes the sequence back to the
original file. **This is a software simulation only** — no real DNA
synthesis, sequencing, or lab work is performed.

## Status

All planned phases (1–22) are complete: file upload, DNA encoding/decoding,
mutation simulation, simplified error correction, storage analysis,
visualization, export/import/report generation, benchmarking, a User Guide,
a Final Dashboard with Presentation Mode, a Phase 13 quality-assurance pass
(bug fixes, integration tests, code audit), a Phase 14 file-identity /
content-hash check, a Phase 15 performance-testing and large-data display
pass, a Phase 16 educational encoding-model comparison, a Phase 17 DNA data
integrity / corruption-detection system, a Phase 18 educational reliability,
redundancy, and recovery simulation, a Phase 19 DNA storage capacity /
information-density / cost comparison, a Phase 20 end-to-end DNA storage
experiment combining every prior stage into one reproducible run, a
Phase 21 Project Showcase / Presentation Mode with viva preparation, a
Phase 22 release-readiness / packaging / setup-verification pass, and a
Phase 23 FastAPI backend exposing the same core logic over HTTP, a
Phase 24 Streamlit ↔ backend integration layer (opt-in via
`BIOVAULT_USE_API`, local mode remains the default), and a Phase 25
production/deployment-readiness pass (configuration, logging, CORS
hardening, upload limits, safe error responses). BioVault is
**deployment-ready** as of Phase 25 — this describes preparation, not
an actual live deployment.

## Main features

- **File Upload** — upload a small `.txt`, `.png`, `.jpg`/`.jpeg` file.
- **DNA Encoding** — convert file bytes into a simulated DNA base sequence.
- **DNA Decoding** — reverse the encoding and confirm exact byte recovery.
- **Mutation Simulator** — simulate substitutions, insertions, or deletions.
- **Error Correction** — add block-checksum redundancy, then detect and
  attempt to correct substitution errors (limitations are shown honestly).
- **Storage Analysis** — theoretical storage-efficiency and overhead figures.
- **DNA Visualization** — base composition and sequence-length charts.
- **Export & Import** — download DNA/metadata/CSV/report files, or import a
  DNA sequence from a `.txt` file for validation/decoding.
- **Benchmarking** — compare original, mutated, and corrected results.
- **Encoding Model Comparison** — compare the real, reversible default
  encoding against three educational, simulated/analysis-only models
  (GC-balancing, homopolymer-run analysis, GC-content analysis).
- **DNA Integrity Check** — validate the current DNA sequence, detect
  possible corruption, and (when the original file is available) confirm
  actual byte-for-byte recovery — plus safe, copy-only demonstration
  scenarios (substitution/insertion/deletion/invalid character/empty/
  truncated).
- **Reliability & Redundancy** — an educational simulation of storing
  multiple redundant DNA copies, corrupting them in a controlled way, and
  attempting recovery via majority vote, agreement-based voting, or the
  existing Phase 6 error correction — with storage-overhead trade-offs
  and a multi-level reliability experiment.
- **DNA Capacity & Storage** — explore theoretical DNA information density
  (2 bits/base), convert file sizes into theoretical DNA lengths, compare
  BioVault's actual encoding against the theoretical ideal, see redundancy
  and error-correction overhead, and view illustrative conventional-storage,
  cost, and physical-mass comparisons — all computed mathematically, even
  at petabyte scale, without allocating giant DNA strings.
- **DNA Storage Experiment** — a reproducible, end-to-end run combining
  encoding, DNA analysis, storage/capacity analysis, redundancy, controlled
  corruption, recovery, integrity verification, and performance measurement
  into one structured result with a downloadable research-style report.
  Reuses every underlying stage's existing module — no second encoding
  algorithm or duplicated formula.
- **Performance & Resources** — run small/medium/large deterministic test
  data through the pipeline and see actual execution time and approximate
  memory use, measured live on your own computer.
- **User Guide** — in-app documentation of every page and concept.
- **Final Dashboard** — a single-page summary of the current experiment,
  overall project progress, and a presentation-ready overview.
- **Project Showcase** — the main presentation/demo page for college
  reviews, seminars, and viva voce: problem statement, objectives,
  workflow diagram, a real encoding example, a Live Demo checklist, the
  biotechnology concepts demonstrated, an explicit "what BioVault does
  NOT do" academic-honesty section, architecture, a project timeline,
  project statistics, a 12-slide presentation outline with speaker notes,
  future scope, and a conclusion.
- **Viva Preparation** — a local, offline 30+ question bank across six
  categories (biotechnology, encoding, error handling, integrity,
  storage/capacity, project) with category browsing, show/hide answers,
  and a random-question option.
- **Environment & Setup Check** — a lightweight, local "is BioVault ready
  to run on this computer?" check: Python version, required dependencies,
  project folder structure, and core-module imports, with plain-language
  troubleshooting guidance if something is missing.

## Folder structure

```
plan-B/
├── app.py                          # Streamlit entry point (page routing)
├── app/
│   ├── config.py                   # Shared constants (title, page config)
│   ├── services/
│   │   └── backend_service.py      # Phase 24: local-vs-API integration layer (non-UI)
│   └── modules/
│       ├── file_handler.py         # File validation (non-UI)
│       ├── dna_encoder.py          # Bytes -> DNA encoding (non-UI)
│       ├── dna_decoder.py          # DNA -> bytes decoding (non-UI)
│       ├── dna_mutator.py          # Mutation simulation (non-UI)
│       ├── dna_error_correction.py # Checksum redundancy/correction (non-UI)
│       ├── storage_analysis.py     # Storage efficiency math (non-UI)
│       ├── dna_visualization.py    # Chart-data preparation (non-UI)
│       ├── data_export.py          # Export/import/report logic (non-UI)
│       ├── benchmarking.py         # Cross-phase comparison (non-UI)
│       ├── project_summary.py      # Final Dashboard logic (non-UI)
│       ├── result_identity.py      # File-identity/staleness matching (non-UI)
│       ├── preview_utils.py        # Safe long-text preview logic (non-UI)
│       ├── performance_analysis.py # Timing/memory benchmarking logic (non-UI)
│       ├── encoding_models.py      # Educational encoding-model comparison (non-UI)
│       ├── dna_integrity.py        # Integrity/corruption-detection logic (non-UI)
│       ├── redundancy_simulation.py # Redundancy/recovery simulation logic (non-UI)
│       ├── capacity_analysis.py    # Storage capacity/density/cost logic (non-UI)
│       ├── experiment_pipeline.py  # End-to-end experiment orchestration (non-UI)
│       ├── showcase_content.py     # Project Showcase static content/stats (non-UI)
│       ├── viva_questions.py       # Viva question bank (non-UI)
│       ├── environment_check.py    # Local setup/readiness checks (non-UI)
│       ├── documentation.py        # User Guide content (non-UI)
│       └── ui_*.py                 # One Streamlit UI page per module above
├── backend/                          # Phase 23: FastAPI backend (optional)
│   ├── main.py                       # FastAPI app, CORS, routers, error handler
│   ├── schemas.py                    # Pydantic request/response models
│   ├── routes/                       # One router module per endpoint group
│   │   ├── health.py
│   │   ├── encoding.py
│   │   ├── decoding.py
│   │   ├── mutation.py
│   │   ├── error_correction.py
│   │   └── analysis.py
│   └── services/
│       └── biovault_service.py       # Shared exception -> HTTP status mapping
├── api/                               # Optional HTTP client for the backend
│   └── client.py                      # Used by app/services/backend_service.py in API mode
├── tests/                           # Pytest suite (mirrors app/modules/*)
├── .streamlit/
│   └── config.toml                  # Safe default Streamlit settings
├── .gitignore
├── .env.example                      # Documented environment-variable template (no real secrets)
├── requirements.txt
├── run_windows.bat                  # One-click Windows setup + launch
├── run_mac_linux.sh                 # One-command macOS/Linux setup + launch
└── README.md
```

Business logic (`app/modules/*.py`, excluding `ui_*.py`) has no Streamlit
dependency and is fully unit-tested; each `ui_*.py` file only handles
presentation and session-state wiring for its matching logic module. The
Phase 23 `backend/` package reuses these exact same `app/modules/*.py`
functions over HTTP — it does not reimplement any algorithm.

## Quick Start (Windows)

Double-click **`run_windows.bat`** (or run it from a terminal). It creates
a virtual environment if needed, installs dependencies, and launches the
app — safe to run multiple times.

## Quick Start (macOS / Linux)

```bash
bash run_mac_linux.sh
```

Does the same thing as the Windows script: creates a virtual environment
if needed, installs dependencies, and launches the app.

## Manual Installation

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

`requirements.txt` lists only the packages BioVault's code actually
imports: `streamlit` and `pandas` to run the app, `pytest` to run the
test suite. If you're unsure whether your setup is ready, open the
**Environment & Setup Check** page after launching the app.

## How to run Streamlit

```bash
streamlit run app.py
```

## How to run the backend API

Development:

```bash
uvicorn backend.main:app --reload
```

Deployment (binds to all interfaces, no auto-reload):

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The backend is **optional** — the Streamlit app above does not require
it and continues to work fully on its own. See the **Backend** and
**Configuration** sections below for details, available endpoints, and
environment variables.

## How to run tests

```bash
python -m pytest -q
```

This runs both the existing Streamlit-logic test suite and the Phase 23
backend API tests together (the backend tests use FastAPI's in-process
`TestClient` plus a real local `uvicorn` server on a dedicated test
port — no manually running server is required to run `pytest`).

**Known warning (investigated, left as-is):** running the test suite
shows a `StarletteDeprecationWarning` recommending a package called
`httpx2` for `starlette.testclient.TestClient`. This only affects test
code (not `api/client.py`'s runtime use of `httpx`, which is
unaffected) and `httpx2` is a very new, separately-maintained package
unrelated to this project's other pinned dependencies. Adding it purely
to silence a test-only warning was judged an unnecessary risk for zero
functional benefit (Phase 25); this can be revisited later if the
warning becomes an error in a future Starlette release.

## Basic user workflow

1. **File Upload** — upload a small text or image file.
2. **DNA Encoding** — generate its simulated DNA sequence.
3. **DNA Decoding** — decode it back and confirm exact byte-for-byte recovery.
4. **Mutation Simulator** — introduce substitutions/insertions/deletions.
5. **Error Correction** — add redundancy and attempt to detect/correct errors.
6. **Storage Analysis** / **DNA Visualization** — inspect efficiency and charts.
7. **Export & Import** — download DNA/metadata/CSV/report files, or import a
   DNA sequence back in.
8. **Benchmarking** — compare original vs. mutated vs. corrected results.
9. **Final Dashboard** — see everything summarized on one page, plus a
   presentation-ready overview of the whole project.

## File identity check

BioVault records a SHA-256 content fingerprint (`content_hash`) for every
uploaded file, alongside its filename. Later pages use this fingerprint --
not just the filename -- to decide whether a stored result (encoding,
mutation, error correction, analysis, benchmarking, etc.) still belongs to
the file currently uploaded. This means uploading a *different* file that
happens to share the same filename as a previous upload never shows stale
results from the old file. This is a simple, self-contained safety check
built into the app -- not an external database, login, or user-account
system.

## Performance & Resources

The **Performance & Resources** page generates deterministic small (~1 KB),
medium (~100 KB), and large (~1 MB) test data and runs it through encoding,
decoding, mutation, error correction, and storage analysis, timing each
step and estimating its peak memory use with Python's built-in
`time.perf_counter()` and `tracemalloc`. Every result is labeled
**"Measured on this computer"** — these numbers depend on your hardware,
Python version, current system load, file size, and the settings used, so
they are never shown as a fixed or universal benchmark.

Pages that display DNA sequences, binary strings, or imported text only
ever show a short preview (the first ~500 characters) for very long data,
with a note stating the total length and how much is hidden. This only
affects what's shown on screen — the complete, untouched data is always
used for decoding, validation, error correction, export, import, and file
recovery. The Phase 14 file-identity/content-hash check is unaffected and
remains fully active.

## Encoding Model Comparison

The **Encoding Model Comparison** page compares BioVault's real, default
encoding against three educational alternatives, using the file already
uploaded and encoded:

- **Model A -- Basic Binary-to-DNA (default):** the real, unmodified
  `00->A, 01->C, 10->G, 11->T` mapping used everywhere else in the app.
  **Reversible** — recovery is actually confirmed, not assumed.
- **Model B -- GC-Balanced (simulated):** demonstrates nudging GC content
  toward 50% by choosing between two valid bit-to-base mapping tables per
  block. **Simulated / analysis-only, not reversible** — the per-block
  choice isn't stored, so this demonstration sequence can never be
  decoded back into a file.
- **Model C -- Homopolymer Analysis:** measures long repeated-base runs
  (e.g. `AAAA`), which can be harder for real DNA sequencing hardware to
  count accurately. **Analysis-only** — it only measures, never changes,
  the sequence.
- **Model D -- GC-Content Analysis:** reports GC%/AT%/homopolymer/invalid-
  character statistics as a standalone reference. **Analysis-only.**

Every result states clearly whether it is reversible or analysis-only,
and whether a figure is measured or an estimate. Models B, C, and D are
**never** used by the real upload → encode → decode → export pipeline —
they exist purely for educational comparison. The page uses the same
Phase 14 file-identity (content-hash) check as every other page, so a
different file sharing the same filename can never produce a stale
comparison result.

## DNA Integrity Check

The **DNA Integrity Check** page validates the current DNA sequence and
reports one of six clear statuses:

| Status | Meaning |
|---|---|
| ✅ Valid | Decodes fine; no recovery claim was requested. |
| ✅ Successfully Recovered | Decodes AND matches the original file's bytes exactly (actually compared, never assumed). |
| ℹ️ Unable to Verify | Decodes fine, but no original file is available to compare against. |
| ⚠️ Incomplete | Only valid bases, but the length can't split into whole bytes (a sign of an insertion/deletion). |
| ❌ Invalid | Empty, or contains characters other than A/T/G/C. |
| ❌ Corrupted | Decodes, but doesn't match the original — or decoding fails unexpectedly. |

Unusual GC content and long homopolymer (repeated-base) runs are always
shown as **warnings** — risk indicators from real DNA-storage research —
never as proof of corruption. The page also offers safe, clearly-labeled
demonstration scenarios (substitution, insertion, deletion, invalid
character, empty sequence, truncated sequence) that run only on a *copy*
of the real DNA sequence; your actual stored sequence is never modified.
This page uses the same Phase 14 content-hash identity check as every
other page.

## Reliability & Redundancy

The **Reliability & Redundancy** page is an **educational simulation** of
a general data-storage idea: storing extra redundant copies can increase
the ability to detect or recover from data loss or corruption. It does
not measure or predict real laboratory DNA-storage performance.

- **Redundancy levels**: No redundancy (1 copy), or 1/2/3 extra copies
  (2/3/4 copies total). More copies mean more storage used — this page
  always shows the storage-overhead cost alongside any reliability
  benefit.
- **Controlled corruption**: substitution, insertion, or deletion, at a
  chosen rate, with an optional fixed seed for reproducibility. Each
  copy is corrupted independently (different per-copy randomness), and
  the original stored DNA sequence is never modified — only copies are
  ever corrupted.
- **Recovery strategies**: **Majority Vote** (pick whichever base most
  copies agree on; ties are marked unresolved, never guessed),
  **Agreement-Based** (require at least a chosen fraction of copies to
  agree, stricter than plain majority), and the existing **Phase 6
  Error Correction** method, for direct side-by-side comparison.
- **Insertions/deletions are detected, not guessed around**: majority/
  agreement voting requires every copy to be the same length. If
  corruption shifts a copy's length, the page reports recovery as
  unavailable/failed rather than comparing the wrong positions.
- **Recovery confirmation**: "recovery percentage" measures how many
  positions had a confident vote outcome — it does **not** by itself
  mean those positions are correct. Only an actual byte-for-byte
  comparison against the original file can confirm **✅ Successfully
  Recovered**; otherwise the page shows ⚠️ Partially Recovered, ❌
  Recovery Failed, or ⚠️ Unable to Verify.
- **Reliability experiment**: automatically runs the simulation across
  multiple redundancy levels and corruption rates and charts Recovery %
  vs. Corruption Level and Storage Overhead vs. Redundancy Level — every
  number comes from actually running the simulation, never hardcoded.

This page uses the same Phase 14 content-hash identity check as every
other page.

## DNA Capacity & Storage

The **DNA Capacity & Storage** page is an educational exploration of DNA
information density and storage trade-offs. Every value is explicitly
labeled as one of:

- **Theoretical** — pure math from the 4-symbol DNA alphabet (2 bits/base
  = log2(4)), before any real-world constraint.
- **Measured** — a real value from the user's uploaded file or BioVault's
  own actual encoding result.
- **Measured vs. theoretical** — a comparison of the two (e.g. actual
  encoded DNA length vs. the theoretical ideal for the same file size).
- **Estimated** — a number computed from user-supplied or clearly
  documented example assumptions (cost, physical mass) — never a claimed
  fact or market quote.

Sections include an information-density overview, a file-size → DNA-length
calculator, an actual-vs-theoretical comparison (using Phase 14 identity
checks so a different file with the same filename is never confused with
a previous result), a redundancy calculator (reusing Phase 18's math
directly, never a duplicated formula), an illustrative conventional-storage
comparison, an optional illustrative cost estimator, scale examples up to
petabyte scale, and an optional physical-mass estimate. All large-scale
examples are pure arithmetic — BioVault never allocates an actual
petabyte-scale DNA string. The page explicitly explains why **theoretical
density is not the same as practical, usable density**, and never claims
DNA storage is currently cheaper, faster, or commercially superior to
conventional storage.

## DNA Storage Experiment

The **DNA Storage Experiment** page combines every prior phase into one
reproducible, end-to-end run:

```
Input File -> File Identity -> DNA Encoding -> DNA Analysis
  -> Storage Analysis -> Capacity Analysis -> Redundancy
  -> Simulated Corruption -> Recovery/Error Correction
  -> Integrity Verification -> Performance Measurement
  -> Final Experiment Result
```

Every stage calls the exact same existing function used on that stage's
own dedicated page — the real encoder/decoder, Phase 16's GC/homopolymer
analysis, Phase 7's storage math, Phase 19's capacity math, Phase 18's
redundancy/corruption/recovery, Phase 17's integrity classification, and
Phase 15's timing/memory measurement. Nothing is reimplemented, so this
page can never disagree with its dedicated counterpart.

The overall status is always one of four honest outcomes — **✅
Successfully Recovered** (only when the recovered bytes are actually
byte-for-byte identical to the original), **❌ Recovery Failed**, **⚠️
Unable to Verify**, or **⚠️ Simulation Completed - Recovery Not
Available** (when an insertion/deletion breaks the alignment
majority/agreement voting needs) — never inferred from a recovery
percentage alone. A full research-style text report can be downloaded,
built entirely from the experiment's real, actual results. Same-session
experiment runs for the current file can be compared side by side, and
the page uses the same Phase 14 content-hash identity check as every
other page.

## Project Showcase

The **Project Showcase** page is the main presentation/demonstration page,
built for college project reviews, biotechnology engineering seminars,
viva voce, project review, classroom presentation, and exhibitions.

**Purpose:** explain BioVault clearly to a beginner (a second-year
Biotechnology Engineering student) while pointing to the real, working
application for an actual demonstration — it is a guide to presenting the
project, not a substitute for running it.

**Demonstration workflow:** a Live Demo checklist (upload → encode → view
DNA → check GC content → mutate → apply redundancy → recover → verify
SHA-256 → compare bytes → generate a report) that walks through the
app's other real pages step by step — nothing on the Showcase page runs
automatically.

**Presentation mode:** a ready-to-use 12-slide outline (Title,
Introduction, Problem Statement, DNA as an Information Medium,
Objectives, Architecture, Encoding/Decoding, Mutation/Error Correction,
Redundancy/Integrity, Capacity/Performance, Live Demonstration,
Conclusion), each with bullet points and a short speaker-note
suggestion, plus a project timeline, project statistics (module/page
counts are counted directly from real project files), and an explicit
"what BioVault does NOT do" section for academic honesty.

## Viva Preparation

The **Viva Preparation** page provides a local, offline question bank
(30+ questions) across six categories — Basic Biotechnology, Computer/
Encoding, Error Handling, Integrity, Storage/Capacity, and Project — for
oral-exam and project-review preparation. Browse by category or jump to
a random question, reveal answers on demand with **Show Answer**, and
track your progress with a simple session indicator. No internet
connection is required; the entire bank is stored locally in the app,
and every answer stays consistent with BioVault's own academic-honesty
stance (never claiming real DNA synthesis, sequencing, or laboratory
validation).

## Environment & Setup Check

The **Environment & Setup Check** page answers "is BioVault ready to run
on this computer?" with fast, local, offline checks:

- **Python version** — confirms a supported interpreter (3.9+).
- **Dependencies** — confirms `streamlit`/`pandas` (required to run the
  app) are installed, and separately notes `pytest` (only needed to run
  the test suite).
- **Project structure** — confirms `app/`, `app/modules/`, and `tests/`
  exist.
- **Core module imports** — confirms a representative sample of
  BioVault's real logic modules import without error.

It never runs the test suite itself (that stays a deliberate, separate
`python -m pytest -q` step) and never accesses the network. If something
is missing, it shows plain-language troubleshooting steps.

## Release Readiness

This project is set up for straightforward setup and sharing:

- **`requirements.txt`** lists only the packages the code actually
  imports — no unused or blindly-added dependencies.
- **`.gitignore`** excludes virtual environments, caches, and editor
  files, so a fresh `git clone` stays clean.
- **`.streamlit/config.toml`** sets safe, project-appropriate defaults
  (matching the app's own upload-size limit; usage-stats collection
  disabled) — it does not enable any network exposure or authentication.
- **`run_windows.bat`** / **`run_mac_linux.sh`** give a one-step setup +
  launch path for someone running BioVault for the first time on a new
  computer.

## Backend

Phase 23 adds an **optional** FastAPI backend that exposes BioVault's
existing core logic over HTTP, so it can be called by other clients (a
future frontend, scripts, automated tools) — not just the Streamlit UI.

**What it is:** a thin HTTP layer (`backend/`) whose routes call the
exact same `app/modules/*.py` functions the Streamlit pages already
use — `dna_encoder.encode_file_to_dna`, `dna_decoder.decode_dna_to_file`,
`dna_mutator.mutate_dna`, `dna_error_correction`'s checksum functions,
and `storage_analysis.analyze_storage_efficiency`. No algorithm is
reimplemented.

**Why it was added:** to make BioVault's core simulation reusable
outside of Streamlit, while keeping the existing app fully working and
independent — the Streamlit UI does not require the backend to be
running.

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Start the backend:**

```bash
uvicorn backend.main:app --reload
```

**API base URL:** `http://127.0.0.1:8000` by default, overridable via
the `BIOVAULT_API_URL` environment variable (see `app/config.py` and
`api/client.py`).

**Available endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness check |
| POST | `/api/encode` | Encode base64 file bytes into DNA |
| POST | `/api/decode` | Decode a DNA sequence back into bytes |
| POST | `/api/mutation` | Simulate substitution/insertion/deletion |
| POST | `/api/error-correction` | Add redundancy and detect/correct errors |
| POST | `/api/storage-analysis` | Compute storage-efficiency figures |
| GET | `/docs` | Interactive Swagger UI |
| GET | `/openapi.json` | OpenAPI schema |

Invalid input returns a clean `400`/`422` with a readable message —
never a raw Python traceback, file path, or other internal detail
(verified by tests that force an unexpected server error and inspect
the response).

**On API versioning:** endpoints currently live under a flat `/api/...`
prefix rather than `/api/v1/...`. This was a deliberate choice reviewed
in Phase 25: BioVault has exactly one backend consumer today (its own
Streamlit app via `api/client.py`) and one deployed version at a time,
so adding version-prefix routing now would add real complexity
(duplicated route registration, client-side version selection) for no
current benefit. If a second, incompatible API version is ever needed,
versioning can be introduced then without disrupting this phase's work.

## Streamlit ↔ Backend Integration

Phase 24 connects the existing Streamlit pages to the backend through a
small integration layer (`app/services/backend_service.py`), controlled
by one configuration flag — **local mode remains the default**, so
nothing changes unless you explicitly opt in.

### Running locally

**Terminal 1 — backend:**

```bash
uvicorn backend.main:app --reload
```

**Terminal 2 — Streamlit:**

```bash
streamlit run app.py
```

### Local mode (default)

```text
BIOVAULT_USE_API=false
```

Streamlit calls `app/modules/*.py` directly, exactly as it always has —
the backend does not even need to be running.

### API mode

```bash
# Windows (PowerShell)
$env:BIOVAULT_USE_API="true"
$env:BIOVAULT_API_URL="http://127.0.0.1:8000"
streamlit run app.py

# macOS/Linux
BIOVAULT_USE_API=true BIOVAULT_API_URL=http://127.0.0.1:8000 streamlit run app.py
```

Streamlit routes encoding, decoding, mutation, error-correction, and
storage-analysis operations through `api/client.py` → the FastAPI
backend → the exact same core functions. **Both modes produce
compatible results** — the integration layer normalizes the API
response (e.g. reconstructing the `binary_str` preview field, decoding
base64 back to raw bytes) so every existing page displays identically
regardless of mode, and Phase 14's `content_hash`/stale-result
protection works unchanged in both.

**Fallback behavior:** if API mode is enabled but the backend is
unreachable, the affected page shows *"⚠️ BioVault backend is
unavailable. Falling back to local processing."* and completes the
operation locally instead of crashing. A genuine input-validation error
returned by the backend (e.g. invalid DNA characters) is shown as a
real validation error, not confused with an outage. When API mode is
on and the backend is reachable, a small `🔌 Backend API mode:
connected` caption appears on the affected pages; in local mode (the
default) nothing extra is shown at all.

## Configuration

All configuration is via environment variables (see `app/config.py`
for defaults, and `.env.example` for a documented placeholder
template — copy it to `.env` and adjust, or set these directly in your
shell/deployment platform; no `.env`-loading library is required to run
BioVault, since it reads `os.environ` directly).

| Variable | Default | Purpose |
|---|---|---|
| `BIOVAULT_API_URL` | `http://127.0.0.1:8000` | Backend base URL used by Streamlit/`api/client.py` |
| `BIOVAULT_USE_API` | `false` | `true` routes Streamlit through the backend; `false` (default) uses direct local calls |
| `BIOVAULT_ENV` | `development` | `development` or `production` — only affects the default log level |
| `BIOVAULT_LOG_LEVEL` | `DEBUG` (dev) / `INFO` (prod) | Backend log verbosity (`DEBUG`/`INFO`/`WARNING`/`ERROR`) |
| `BIOVAULT_CORS_ORIGINS` | *(empty)* | Comma-separated extra allowed CORS origins; empty keeps the default localhost-only behavior. Never set to `*` |
| `BIOVAULT_MAX_UPLOAD_MB` | `2` | Maximum file size the backend's `/api/encode` accepts |

There are no secrets, API keys, or credentials anywhere in this
project — every variable above is a plain setting, safe to see in
logs or version control (only real `.env` files with actual deployment
values are gitignored, as a general good practice).

## Deployment

BioVault's Streamlit app and FastAPI backend are **separate processes**
that can be deployed independently:

- **Streamlit only** (simplest): deploy `app.py` alone with
  `BIOVAULT_USE_API=false` (the default) — no backend needed at all.
  This is the lowest-effort deployment for demos, classrooms, or a
  single-service platform (e.g. Streamlit Community Cloud).
- **Streamlit + backend**: run `uvicorn backend.main:app --host 0.0.0.0
  --port 8000` as one service and `streamlit run app.py` as another
  (with `BIOVAULT_USE_API=true` and `BIOVAULT_API_URL` pointing at the
  backend's real address), on the same host or two separate ones. Set
  `BIOVAULT_CORS_ORIGINS` to the Streamlit service's real origin if
  they're on different domains, and `BIOVAULT_ENV=production` /
  `BIOVAULT_LOG_LEVEL=INFO` for quieter logs.

This project intentionally does **not** include Docker, Kubernetes, or
any cloud-database configuration — none of it is required for either
deployment shape above, and adding it now would be unused complexity.
**This section describes how to deploy BioVault; it has not been
deployed as part of this phase.**

## Known limitations

- The DNA encoding scheme (2 bits per base) is a simplified educational
  scheme, not a real biochemical storage format.
- Error correction uses a simplified checksum method: at most one
  substitution per block can be corrected, and only when the fix is
  unambiguous. Checksum collisions can make some errors uncorrectable
  by design.
- Insertions and deletions cannot be corrected — only detected as a
  structural length mismatch.
- No real DNA synthesis, sequencing, or laboratory validation is performed.
- All results depend on this project's own simulation assumptions.

## Educational disclaimer

BioVault is a **simulation and educational platform**. It is **not** a real
DNA synthesis, sequencing, or laboratory data-storage system, and none of
its figures represent real-world DNA storage costs or capabilities.
