"""
Tests for app/modules/environment_check.py (Phase 22).

Covers Python-version checking, dependency-import checking, project-
directory checking, core-module-import checking, and the combined
overall-status result. Never runs pytest from within the checker
(that would be circular) and never depends on network access.
"""

import sys

from app.modules.environment_check import (
    MINIMUM_PYTHON_VERSION,
    REQUIRED_RUNTIME_PACKAGES,
    DEV_ONLY_PACKAGES,
    REQUIRED_DIRECTORIES,
    CORE_MODULE_NAMES,
    STATUS_READY,
    STATUS_ISSUES_FOUND,
    check_python_version,
    check_dependencies,
    check_directories,
    check_core_imports,
    run_environment_check,
)


# --- Python version -----------------------------------------------------------------

def test_check_python_version_reports_current_version():
    result = check_python_version()
    current = f"{sys.version_info[0]}.{sys.version_info[1]}"
    assert result["python_version"] == current


def test_check_python_version_matches_minimum_constant():
    result = check_python_version()
    assert result["minimum_required"] == f"{MINIMUM_PYTHON_VERSION[0]}.{MINIMUM_PYTHON_VERSION[1]}"


def test_check_python_version_is_supported_on_this_test_runner():
    # The test suite itself is running on a supported interpreter, so
    # this must report True on the machine that runs pytest.
    result = check_python_version()
    assert result["python_supported"] is True


# --- Dependencies ----------------------------------------------------------------------

def test_check_dependencies_covers_every_declared_package():
    results = check_dependencies()
    names = {entry["name"] for entry in results}
    assert names == set(REQUIRED_RUNTIME_PACKAGES) | set(DEV_ONLY_PACKAGES)


def test_check_dependencies_marks_runtime_packages_as_required():
    results = check_dependencies()
    for entry in results:
        if entry["name"] in REQUIRED_RUNTIME_PACKAGES:
            assert entry["required"] is True
        if entry["name"] in DEV_ONLY_PACKAGES:
            assert entry["required"] is False


def test_check_dependencies_all_importable_in_this_environment():
    # Since this test is running via pytest, streamlit/pandas/pytest
    # must all already be installed and importable here.
    results = check_dependencies()
    for entry in results:
        assert entry["importable"] is True
        assert entry["error"] is None


# --- Directories -------------------------------------------------------------------------

def test_check_directories_covers_every_declared_directory():
    results = check_directories()
    paths = {entry["path"] for entry in results}
    assert paths == set(REQUIRED_DIRECTORIES)


def test_check_directories_all_exist_in_this_project():
    results = check_directories()
    for entry in results:
        assert entry["exists"] is True


# --- Core imports ---------------------------------------------------------------------------

def test_check_core_imports_covers_every_declared_module():
    results = check_core_imports()
    names = {entry["name"] for entry in results}
    assert names == set(CORE_MODULE_NAMES)


def test_check_core_imports_all_succeed():
    results = check_core_imports()
    for entry in results:
        assert entry["importable"] is True
        assert entry["error"] is None


# --- Combined result -------------------------------------------------------------------------

def test_run_environment_check_structure():
    result = run_environment_check()
    for key in (
        "python_version", "python_supported", "minimum_python_required",
        "dependencies", "directories", "core_imports", "overall_status",
    ):
        assert key in result


def test_run_environment_check_reports_ready_in_this_working_environment():
    result = run_environment_check()
    assert result["overall_status"] == STATUS_READY


def test_overall_status_is_one_of_the_two_documented_values():
    result = run_environment_check()
    assert result["overall_status"] in (STATUS_READY, STATUS_ISSUES_FOUND)


def test_run_environment_check_is_deterministic_for_same_environment():
    first = run_environment_check()
    second = run_environment_check()
    assert first == second


def test_run_environment_check_never_raises():
    # The checker must be safe to call unconditionally from a
    # Streamlit page load -- it should never itself throw.
    try:
        run_environment_check()
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(f"run_environment_check() raised unexpectedly: {exc}")
