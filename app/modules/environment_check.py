"""
Lightweight local runtime-environment checker (non-UI, no Streamlit
dependency).

Answers one beginner-friendly question -- "Is BioVault ready to run on
this computer?" -- by checking the Python version, whether the
project's actual runtime dependencies are importable, whether the
expected project directories exist, and whether BioVault's own core
modules import cleanly.

This is intentionally lightweight: it never runs pytest, never
downloads anything, and never performs expensive diagnostics. Every
check is a fast, local import/existence check suitable for running
every time the Streamlit page loads.
"""

import importlib
import sys
from pathlib import Path

# Python versions BioVault is expected to run correctly on. Kept as a
# simple minimum-version check (no upper bound assumed) since the
# project uses no version-specific language features beyond this.
MINIMUM_PYTHON_VERSION = (3, 9)

# Only the packages BioVault's application code actually imports at
# runtime -- pytest is a development/testing tool, not required to run
# the Streamlit app itself, so it is intentionally checked separately.
REQUIRED_RUNTIME_PACKAGES = ("streamlit", "pandas")
DEV_ONLY_PACKAGES = ("pytest",)

# Directories expected to exist relative to the project root (the
# parent of the "app" package this module lives in).
REQUIRED_DIRECTORIES = ("app", "app/modules", "tests")

# A representative sample of BioVault's own core modules -- covering
# the real encode/decode pipeline plus each major phase's logic module
# -- used to confirm the application's own code imports cleanly, not
# just its third-party dependencies.
CORE_MODULE_NAMES = (
    "app.config",
    "app.modules.file_handler",
    "app.modules.dna_encoder",
    "app.modules.dna_decoder",
    "app.modules.dna_mutator",
    "app.modules.dna_error_correction",
    "app.modules.dna_integrity",
    "app.modules.redundancy_simulation",
    "app.modules.capacity_analysis",
    "app.modules.experiment_pipeline",
)

STATUS_READY = "ready"
STATUS_ISSUES_FOUND = "issues_found"


def _project_root() -> Path:
    """Return the project root directory (two levels up from this file:
    app/modules/environment_check.py -> project root)."""
    return Path(__file__).resolve().parent.parent.parent


def check_python_version() -> dict:
    """Check the running Python version against BioVault's minimum."""
    current_version = sys.version_info[:2]
    supported = current_version >= MINIMUM_PYTHON_VERSION

    return {
        "python_version": f"{current_version[0]}.{current_version[1]}",
        "minimum_required": f"{MINIMUM_PYTHON_VERSION[0]}.{MINIMUM_PYTHON_VERSION[1]}",
        "python_supported": supported,
    }


def check_dependencies() -> list:
    """Check whether each required runtime package can actually be
    imported, returning one result entry per package.

    Only reports import success/failure -- it never inspects or
    compares exact installed version numbers against requirements.txt
    (that is what `pip install -r requirements.txt` itself already
    guarantees when run correctly).
    """
    results = []
    for package_name in REQUIRED_RUNTIME_PACKAGES:
        results.append(_check_single_import(package_name, required=True))
    for package_name in DEV_ONLY_PACKAGES:
        results.append(_check_single_import(package_name, required=False))
    return results


def _check_single_import(module_name: str, required: bool) -> dict:
    try:
        importlib.import_module(module_name)
        return {"name": module_name, "importable": True, "required": required, "error": None}
    except ImportError as exc:
        return {"name": module_name, "importable": False, "required": required, "error": str(exc)}


def check_directories() -> list:
    """Check that each expected project directory exists on disk."""
    root = _project_root()
    results = []
    for relative_path in REQUIRED_DIRECTORIES:
        path = root / relative_path
        results.append({"path": relative_path, "exists": path.is_dir()})
    return results


def check_core_imports() -> list:
    """Check that each of BioVault's own core modules imports cleanly."""
    results = []
    for module_name in CORE_MODULE_NAMES:
        try:
            importlib.import_module(module_name)
            results.append({"name": module_name, "importable": True, "error": None})
        except Exception as exc:  # noqa: BLE001 -- report any import-time failure, not just ImportError
            results.append({"name": module_name, "importable": False, "error": str(exc)})
    return results


def run_environment_check() -> dict:
    """Run every check and return one structured result.

    `overall_status` is "ready" only when the Python version is
    supported, every REQUIRED runtime dependency imports successfully,
    every expected directory exists, and every core module imports
    successfully. A missing dev-only package (pytest) does not affect
    readiness to *run* the app, only to run its test suite.
    """
    python_check = check_python_version()
    dependency_checks = check_dependencies()
    directory_checks = check_directories()
    core_import_checks = check_core_imports()

    required_dependencies_ok = all(
        entry["importable"] for entry in dependency_checks if entry["required"]
    )
    directories_ok = all(entry["exists"] for entry in directory_checks)
    core_imports_ok = all(entry["importable"] for entry in core_import_checks)

    overall_ready = (
        python_check["python_supported"]
        and required_dependencies_ok
        and directories_ok
        and core_imports_ok
    )

    return {
        "python_version": python_check["python_version"],
        "python_supported": python_check["python_supported"],
        "minimum_python_required": python_check["minimum_required"],
        "dependencies": dependency_checks,
        "directories": directory_checks,
        "core_imports": core_import_checks,
        "overall_status": STATUS_READY if overall_ready else STATUS_ISSUES_FOUND,
    }
