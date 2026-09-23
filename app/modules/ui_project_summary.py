"""
UI module: Final Dashboard page.

Summarizes the current experiment (file, encoding, mutation, error
correction, storage analysis, benchmarking) using real session-state
data, shows a project-progress checklist, and provides a
presentation-friendly summary of the whole BioVault project. All
calculations/content live in project_summary.py -- this file only
handles presentation.
"""

import streamlit as st

from app.modules.project_summary import (
    build_dashboard_summary,
    get_experiment_status,
    get_project_progress,
    get_presentation_content,
)
from app.modules.result_identity import file_identity_matches, result_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY
from app.modules.ui_dna_mutation import MUTATION_SESSION_KEY
from app.modules.ui_error_correction import CORRECTION_SESSION_KEY
from app.modules.ui_storage_analysis import ANALYSIS_SESSION_KEY
from app.modules.ui_benchmarking import BENCHMARK_SESSION_KEY

PROJECT_SUMMARY_SESSION_KEY = "project_summary_result"

NOT_AVAILABLE = "Not available"


def render_project_summary() -> None:
    """Render the Final Dashboard page."""

    st.header("🏠 Final Dashboard")
    st.write(
        "A single-page summary of your current BioVault experiment, the "
        "project's overall workflow, and a presentation-ready overview of "
        "the whole platform."
    )
    st.info(
        "BioVault is a **simulation and educational platform** -- not a "
        "real DNA synthesis, sequencing, or laboratory storage system.",
        icon="⚠️",
    )

    file_info = st.session_state.get(UPLOAD_SESSION_KEY)
    encoding_result = st.session_state.get(ENCODING_SESSION_KEY)

    encoding_matches = file_identity_matches(file_info, encoding_result)
    dna_sequence = encoding_result["dna_sequence"] if encoding_matches else None

    mutation_result = _get_matching(MUTATION_SESSION_KEY, file_info, "original_dna_sequence", dna_sequence)
    correction_result = _get_matching(CORRECTION_SESSION_KEY, file_info, "original_dna_sequence", dna_sequence)
    analysis_result = _get_matching(ANALYSIS_SESSION_KEY, file_info, "dna_sequence", dna_sequence)
    benchmarking_result = _get_matching(BENCHMARK_SESSION_KEY, file_info, "dna_sequence", dna_sequence)

    summary = build_dashboard_summary(
        file_info if encoding_matches or file_info else None,
        encoding_result if encoding_matches else None,
        mutation_result,
        correction_result,
        analysis_result,
        benchmarking_result,
    )
    status = get_experiment_status(
        file_info,
        encoding_result if encoding_matches else None,
        mutation_result,
        correction_result,
        benchmarking_result,
    )

    st.session_state[PROJECT_SUMMARY_SESSION_KEY] = {
        "source_filename": file_info["filename"] if file_info else None,
        "content_hash": file_info["content_hash"] if file_info else None,
        "status": status,
    }

    _render_status_banner(status)
    _render_dashboard(summary)
    st.divider()
    _render_progress_overview()
    st.divider()
    _render_presentation_mode()


def _get_matching(session_key: str, file_info, dna_field: str, dna_sequence):
    """Return a stored result only if it matches the current file identity
    (filename + content hash) and the current DNA sequence."""
    if file_info is None or dna_sequence is None:
        return None
    result = st.session_state.get(session_key)
    if not result_matches(file_info, result, dna_field, dna_sequence):
        return None
    return result


def _render_status_banner(status: str) -> None:
    st.subheader("Current Experiment Status")
    icons = {
        "No file uploaded": "⬜",
        "File uploaded but not encoded": "🟡",
        "DNA encoded": "🟢",
        "Mutation experiment available": "🟢",
        "Error-correction result available": "🟢",
        "Benchmark available": "✅",
    }
    st.info(f"{icons.get(status, 'ℹ️')} **{status}**")


def _cell(value, suffix: str = ""):
    return f"{value}{suffix}" if value is not None else NOT_AVAILABLE


def _render_dashboard(summary: dict) -> None:
    st.subheader("Experiment Summary")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**📁 File Information**")
            file_summary = summary["file_summary"]
            if file_summary:
                st.write(f"Filename: {_cell(file_summary['filename'])}")
                st.write(f"Size: {_cell(file_summary['size_bytes'], ' bytes')}")
                st.write(f"Type: {_cell(file_summary['category'])}")
            else:
                st.write(NOT_AVAILABLE)

    with col2:
        with st.container(border=True):
            st.markdown("**🧬 DNA Encoding**")
            encoding_summary = summary["encoding_summary"]
            if encoding_summary:
                st.write(f"DNA length: {_cell(encoding_summary['dna_length'], ' bases')}")
                st.write(f"Binary bits: {_cell(encoding_summary['binary_length_bits'], ' bits')}")
            else:
                st.write(NOT_AVAILABLE)

    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown("**🔬 Mutation Experiment**")
            mutation_summary = summary["mutation_summary"]
            if mutation_summary:
                st.write(f"Type: {_cell(mutation_summary['mutation_type'])}")
                st.write(f"Rate: {_cell(mutation_summary['mutation_rate'], '%')}")
                st.write(f"Mutated length: {_cell(mutation_summary['mutated_length'], ' bases')}")
                st.write(f"Total edits: {_cell(mutation_summary['total_edits'])}")
            else:
                st.write(NOT_AVAILABLE)

    with col4:
        with st.container(border=True):
            st.markdown("**🛡️ Error-Correction Experiment**")
            correction_summary = summary["correction_summary"]
            if correction_summary:
                st.write(f"Protected length: {_cell(correction_summary['protected_length'], ' bases')}")
                st.write(f"Corrected length: {_cell(correction_summary['corrected_length'], ' bases')}")
                st.write(f"Errors detected: {_cell(correction_summary['errors_detected'])}")
                st.write(f"Errors corrected: {_cell(correction_summary['errors_corrected'])}")
                if correction_summary["recovery_confirmed"]:
                    st.success("✅ Recovery confirmed successful.")
                else:
                    st.warning("⚠️ Recovery not confirmed successful.")
            else:
                st.write(NOT_AVAILABLE)

    col5, col6 = st.columns(2)
    with col5:
        with st.container(border=True):
            st.markdown("**📊 Storage Analysis**")
            storage_summary = summary["storage_summary"]
            if storage_summary:
                st.write(f"Raw efficiency: {_cell(storage_summary['raw_efficiency_percent'], '%')}")
                st.write(f"Overhead: {_cell(storage_summary['overhead_percent'], '%')}")
            else:
                st.write(NOT_AVAILABLE)

    with col6:
        with st.container(border=True):
            st.markdown("**📈 Benchmarking**")
            benchmarking_summary = summary["benchmarking_summary"]
            if benchmarking_summary:
                st.write("Status: Available")
                st.write(f"Mutation data included: {'Yes' if benchmarking_summary['has_mutation_data'] else 'No'}")
                st.write(f"Correction data included: {'Yes' if benchmarking_summary['has_correction_data'] else 'No'}")
            else:
                st.write(NOT_AVAILABLE)


def _render_progress_overview() -> None:
    st.subheader("Project Progress Overview")
    st.caption("This lists BioVault's overall page workflow (Phases 1-11), not a per-user completion checklist.")
    stages = get_project_progress()
    for i, stage in enumerate(stages, start=1):
        st.write(f"{i}. ✅ {stage}")


def _render_presentation_mode() -> None:
    st.subheader("🎤 Presentation Mode")
    content = get_presentation_content()

    st.markdown(f"### {content['title']}")
    st.warning(content["simulation_disclaimer"], icon="⚠️")

    with st.expander("Problem Statement", expanded=True):
        st.write(content["problem_statement"])

    with st.expander("Objectives"):
        for item in content["objectives"]:
            st.write(f"- {item}")

    with st.expander("Main Workflow"):
        st.write(" → ".join(content["workflow"]))

    with st.expander("Technologies Used"):
        st.write(", ".join(content["technologies"]))

    with st.expander("Major Features"):
        for item in content["workflow"]:
            st.write(f"- {item}")

    with st.expander("Educational Significance"):
        st.write(content["educational_significance"])

    with st.expander("Current Limitations"):
        for item in content["limitations"]:
            st.write(f"- {item}")

    with st.expander("Future Improvement Ideas (not implemented)"):
        st.caption("These are ideas for possible future work -- none of them are implemented in BioVault today.")
        for item in content["future_improvements"]:
            st.write(f"- {item}")
