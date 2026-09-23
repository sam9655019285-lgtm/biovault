"""
UI module: DNA Visualization page.

Pulls together already-generated results from Phases 3, 5, 6, and 7
(session state) and renders charts/tables using dna_visualization.py
for all calculations. This file only handles presentation -- it never
computes statistics itself.
"""

import streamlit as st

from app.modules.dna_visualization import (
    DNAVisualizationError,
    prepare_base_composition_data,
    prepare_length_comparison_data,
    prepare_mutation_statistics_data,
    prepare_error_correction_data,
    prepare_storage_overhead_data,
)
from app.modules.result_identity import file_identity_matches, result_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY
from app.modules.ui_dna_mutation import MUTATION_SESSION_KEY
from app.modules.ui_error_correction import CORRECTION_SESSION_KEY
from app.modules.ui_storage_analysis import ANALYSIS_SESSION_KEY

VISUALIZATION_SESSION_KEY = "dna_visualization_result"


def render_dna_visualization() -> None:
    """Render the DNA Visualization page."""

    st.header("📈 DNA Visualization")
    st.write(
        "Explore charts built from the actual DNA sequences and results "
        "generated on the previous pages -- base composition, length "
        "changes, mutation impact, error correction, and storage overhead."
    )
    st.info(
        "These visualizations represent **computational DNA-storage "
        "simulations**. They are not measurements from real biological "
        "DNA experiments.",
        icon="⚠️",
    )

    file_info = st.session_state.get(UPLOAD_SESSION_KEY)
    encoding_result = st.session_state.get(ENCODING_SESSION_KEY)

    if file_info is None or encoding_result is None:
        st.info(
            "Please upload a file on **File Upload** and generate a DNA "
            "sequence on **DNA Encoding** first."
        )
        return

    if not file_identity_matches(file_info, encoding_result):
        st.info(
            "The DNA sequence in memory doesn't match the currently "
            "uploaded file. Please re-encode it on the **DNA Encoding** page."
        )
        return

    dna_sequence = encoding_result["dna_sequence"]
    st.caption(f"Source file: **{file_info['filename']}**")

    if len(dna_sequence) == 0:
        st.info("The encoded DNA sequence is empty -- nothing to visualize.")
        return

    # Gather optional results, only if they actually belong to the
    # currently-active file/DNA sequence (avoids showing stale charts
    # from a previously uploaded file).
    mutation_result = _get_matching(MUTATION_SESSION_KEY, file_info, "original_dna_sequence", dna_sequence)
    correction_result = _get_matching(CORRECTION_SESSION_KEY, file_info, "original_dna_sequence", dna_sequence)
    analysis_result = _get_matching(ANALYSIS_SESSION_KEY, file_info, "dna_sequence", dna_sequence)

    st.session_state[VISUALIZATION_SESSION_KEY] = {
        "source_filename": file_info["filename"],
        "content_hash": file_info["content_hash"],
        "dna_sequence": dna_sequence,
    }

    _render_base_composition(dna_sequence)
    _render_length_comparison(dna_sequence, mutation_result, correction_result)
    _render_mutation_analytics(mutation_result)
    _render_error_correction_analytics(correction_result)
    _render_storage_overhead(analysis_result)
    _render_limitations()


def _get_matching(session_key: str, file_info: dict, dna_field: str, dna_sequence: str):
    """Return a stored result only if it matches the current file identity
    (filename + content hash) and the current DNA sequence."""
    result = st.session_state.get(session_key)
    if not result_matches(file_info, result, dna_field, dna_sequence):
        return None
    return result


# --- A. DNA Base Composition -----------------------------------------------

def _render_base_composition(dna_sequence: str) -> None:
    st.subheader("A. DNA Base Composition")
    try:
        composition = prepare_base_composition_data(dna_sequence)
    except DNAVisualizationError as exc:
        st.error(f"❌ Could not analyze base composition: {exc}")
        return

    total = int(composition["Count"].sum())
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Bases", f"{total:,}")
    for col, base in zip((col2, col3, col4, col5), ("A", "T", "G", "C")):
        row = composition[composition["Base"] == base].iloc[0]
        col.metric(base, f"{int(row['Count']):,}", f"{row['Percentage']}%")

    st.bar_chart(composition.set_index("Base")["Count"])
    st.caption("📎 Base percentages are rounded to 2 decimals, so their sum may differ from exactly 100% by a tiny fraction.")

    with st.expander("Exact counts and percentages"):
        st.dataframe(composition, hide_index=True, use_container_width=True)


# --- B. DNA Length Comparison ------------------------------------------------

def _render_length_comparison(dna_sequence: str, mutation_result, correction_result) -> None:
    st.subheader("B. DNA Length Comparison")

    mutated_length = mutation_result["stats"]["mutated_length"] if mutation_result else None
    protected_length = None
    if correction_result is not None:
        protected_length = len(correction_result.get("protected_sequence") or "") or None

    try:
        comparison = prepare_length_comparison_data(len(dna_sequence), mutated_length, protected_length)
    except DNAVisualizationError as exc:
        st.error(f"❌ Could not build length comparison: {exc}")
        return

    st.bar_chart(comparison.set_index("Stage")["Length (bases)"])
    st.dataframe(comparison, hide_index=True, use_container_width=True)

    if mutated_length is None:
        st.caption("ℹ️ Mutation data is not available. Run **Phase 5 (Mutation Simulator)** first.")
    if protected_length is None:
        st.caption("ℹ️ Protected DNA length is not available. Run **Phase 6 (Error Correction)** first.")


# --- C. Mutation Analytics ------------------------------------------------------

def _render_mutation_analytics(mutation_result) -> None:
    st.subheader("C. Mutation Analytics")

    if mutation_result is None:
        st.info(
            "No mutation simulation is currently available.\n\n"
            "Run **Phase 5 (Mutation Simulator)** first to view mutation analytics."
        )
        return

    prepared = prepare_mutation_statistics_data(mutation_result["stats"])
    if prepared is None:
        st.warning("Mutation data was found but is missing required fields.")
        return

    summary = prepared["summary"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Mutation Type", summary["mutation_type"].capitalize())
    col2.metric("Mutation Rate", f"{summary['mutation_rate']}%")
    col3.metric("Total Simulated Edits", summary["total_edits"])

    col4, col5, col6 = st.columns(3)
    col4.metric("Original Length", f"{summary['original_length']:,} bases")
    col5.metric("Mutated Length", f"{summary['mutated_length']:,} bases")
    col6.metric("Length Difference", f"{summary['length_difference']:+d} bases")

    st.bar_chart(prepared["edit_breakdown"].set_index("Edit Type")["Count"])

    if summary["length_changed"]:
        st.caption("⚠️ The sequence length changed (insertion/deletion occurred).")
    else:
        st.caption("ℹ️ The sequence length did not change (substitution-only, or no edits applied).")


# --- D. Error-Correction Analytics ------------------------------------------------

def _render_error_correction_analytics(correction_result) -> None:
    st.subheader("D. Error-Correction Analytics")

    if correction_result is None:
        st.info(
            "No error-correction result is available.\n\n"
            "Run **Phase 6 (Error Correction)** first to view correction analytics."
        )
        return

    prepared = prepare_error_correction_data(correction_result["correction"])
    if prepared is None:
        st.warning("Error-correction data was found but is missing required fields.")
        return

    summary = prepared["summary"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Block Size", correction_result.get("block_size", "N/A"))
    col2.metric("Redundancy Size", correction_result.get("redundancy_size", "N/A"))
    col3.metric("Blocks Checked", summary["blocks_checked"])

    col4, col5, col6 = st.columns(3)
    col4.metric("Errors Detected", summary["errors_detected"] if summary["errors_detected"] is not None else "Unknown")
    col5.metric("Errors Corrected", summary["errors_corrected"])
    col6.metric("Uncorrectable Errors", summary["uncorrectable_errors"] if summary["uncorrectable_errors"] is not None else "Unknown")

    st.bar_chart(prepared["breakdown"].set_index("Outcome")["Count"])

    if summary["correction_success"]:
        st.success("✅ Correction succeeded for all detected errors.")
    else:
        st.error("❌ Correction did not succeed for all detected errors.")

    st.caption(
        "📎 This correction method is a **simplified, educational** "
        "single-substitution-per-block checksum scheme -- not a "
        "production-grade or biologically accurate error-correcting code."
    )


# --- E. Storage Overhead --------------------------------------------------------------

def _render_storage_overhead(analysis_result) -> None:
    st.subheader("E. Storage Overhead")

    if analysis_result is None:
        st.info(
            "No storage-analysis result is available.\n\n"
            "Run **Phase 7 (Storage Analysis)** first to view storage overhead."
        )
        return

    prepared = prepare_storage_overhead_data(analysis_result["report"])
    if prepared is None:
        st.warning("Storage-analysis data was found but is missing required fields.")
        return

    summary = prepared["summary"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Original File Size", f"{summary['file_size_bytes']:,} bytes")
    col2.metric("Encoded DNA Length", f"{summary['dna_length']:,} bases")
    col3.metric("Raw Theoretical Efficiency", f"{summary['raw_efficiency_percent']}%")

    if summary["redundancy_bases"] is not None:
        col4, col5 = st.columns(2)
        col4.metric("Redundancy Bases", f"{summary['redundancy_bases']:,}")
        col5.metric("Overhead", f"{summary['overhead_percent']}%")

    st.bar_chart(prepared["breakdown"].set_index("Metric")["Bases"])

    st.caption(
        "📎 **Raw theoretical encoding efficiency** (above) measures only "
        "whether this project's 2-bit-per-base mapping wastes any of its "
        "own capacity -- it is **not** the same as practical biological "
        "DNA storage efficiency, which also depends on synthesis, "
        "sequencing, addressing, and error-correction overhead not "
        "modeled here."
    )


# --- F. Educational Limitations --------------------------------------------------------

def _render_limitations() -> None:
    st.subheader("F. Educational Limitations")
    st.markdown(
        """
        - These charts visualize **simulated computational data**, not
          measurements from real biological DNA experiments.
        - DNA base composition shown here says nothing about the
          biological or chemical stability of a real DNA molecule.
        - Mutation results depend entirely on the mutation type, rate,
          and random seed chosen on the **Mutation Simulator** page --
          different settings will produce different outcomes.
        - Error correction is limited by the simplified checksum method
          used on the **Error Correction** page (see its own limitations).
        - Storage overhead does not include real-world DNA synthesis or
          sequencing costs, primers, indexing, or addressing metadata.
        """
    )
