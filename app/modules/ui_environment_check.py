"""
UI module: Environment & Setup Check page.

Answers a simple beginner-friendly question -- "Is BioVault ready to
run on this computer?" -- by running environment_check.py's lightweight
checks (Python version, dependencies, project directories, core module
imports) and showing the result with plain status indicators and
troubleshooting guidance. This file only handles presentation; all
checking logic lives in environment_check.py.
"""

import streamlit as st

from app.modules.environment_check import (
    STATUS_READY,
    run_environment_check,
)


def render_environment_check() -> None:
    """Render the Environment & Setup Check page."""

    st.header("🛠️ Environment & Setup Check")
    st.write(
        "A quick, local check confirming BioVault is ready to run on "
        "this computer -- no internet connection is used, and nothing "
        "here modifies your system."
    )

    result = run_environment_check()

    if result["overall_status"] == STATUS_READY:
        st.success("✅ BioVault is ready to run on this computer.")
    else:
        st.error("❌ Some setup issues were found -- see the details below.")

    _render_python_version(result)
    _render_dependencies(result)
    _render_directories(result)
    _render_core_imports(result)
    _render_troubleshooting(result)


def _render_python_version(result: dict) -> None:
    st.subheader("Python Version")
    col1, col2 = st.columns(2)
    col1.metric("Detected Version", result["python_version"])
    col2.metric("Minimum Required", result["minimum_python_required"])

    if result["python_supported"]:
        st.success("✅ Python version is supported.")
    else:
        st.error(
            f"❌ Python {result['python_version']} is older than the minimum "
            f"supported version ({result['minimum_python_required']}). "
            "Please install a newer Python version."
        )


def _render_dependencies(result: dict) -> None:
    st.subheader("Dependencies")
    for entry in result["dependencies"]:
        label = entry["name"] + (" (required)" if entry["required"] else " (development/testing only)")
        if entry["importable"]:
            st.write(f"✅ {label}")
        elif entry["required"]:
            st.write(f"❌ {label} -- not installed")
        else:
            st.write(f"⚠️ {label} -- not installed (only needed to run the test suite)")


def _render_directories(result: dict) -> None:
    st.subheader("Project Structure")
    for entry in result["directories"]:
        if entry["exists"]:
            st.write(f"✅ `{entry['path']}/` found")
        else:
            st.write(f"❌ `{entry['path']}/` is missing")


def _render_core_imports(result: dict) -> None:
    st.subheader("Core Module Import Check")
    failures = [entry for entry in result["core_imports"] if not entry["importable"]]

    if not failures:
        st.success(f"✅ All {len(result['core_imports'])} checked core modules imported successfully.")
    else:
        st.error(f"❌ {len(failures)} core module(s) failed to import.")
        for entry in failures:
            st.write(f"- `{entry['name']}`: {entry['error']}")

    with st.expander("Show all checked modules"):
        for entry in result["core_imports"]:
            st.write(f"{'✅' if entry['importable'] else '❌'} `{entry['name']}`")


def _render_troubleshooting(result: dict) -> None:
    if result["overall_status"] == STATUS_READY:
        return

    st.subheader("Troubleshooting Guidance")
    st.markdown(
        """
        - **Python version too old:** install a supported Python version
          (see the minimum above), then recreate your virtual environment.
        - **A required dependency is missing:** run
          `pip install -r requirements.txt` inside your project's virtual
          environment.
        - **A project directory is missing:** make sure you're running
          BioVault from the project's root folder (the one containing
          `app.py`), and that no folder was accidentally deleted or
          renamed.
        - **A core module fails to import:** this usually means a file was
          moved, renamed, or has a syntax error -- check the error message
          above for the exact file and reason.

        If the issue persists, re-download or re-clone the project and
        follow the setup instructions in `README.md` from a clean folder.
        """
    )
