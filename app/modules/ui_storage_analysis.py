"""
UI module: Storage Analysis page.

Reads the file/encoding info already in session state (Phases 2-3) and,
when available, the Phase 5 mutation result and Phase 6 redundancy
settings, then presents a computational storage-efficiency breakdown
using storage_analysis.py. All calculations live in that module; this
file only handles presentation.
"""

import pandas as pd
import streamlit as st

from app.modules.storage_analysis import (
    StorageAnalysisError,
    DNA_BASES_PER_BYTE,
    analyze_storage_efficiency,
    format_bytes,
)
from app.modules.dna_error_correction import DEFAULT_BLOCK_SIZE, DEFAULT_REDUNDANCY_SIZE, MAX_BLOCK_SIZE, MAX_REDUNDANCY_SIZE
from app.modules.result_identity import file_identity_matches, result_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY
from app.modules.ui_dna_mutation import MUTATION_SESSION_KEY
from app.services import backend_service

ANALYSIS_SESSION_KEY = "dna_storage_analysis_result"


def render_storage_analysis() -> None:
    """Render the Storage Analysis page."""

    st.header("📊 Storage Analysis")
    st.write(
        "Compare the original file size, binary representation, DNA "
        "sequence length, and error-correction overhead using the data "
        "already generated on the previous pages."
    )
    st.info(
        "DNA storage efficiency depends on encoding, redundancy, "
        "addressing, metadata, synthesis, sequencing, and error-correction "
        "overhead. This page shows a **simplified computational estimate "
        "only**.",
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

    _render_backend_status_caption()
    block_size, redundancy_size = _render_redundancy_controls()

    mutation_result = st.session_state.get(MUTATION_SESSION_KEY)
    mutation_available = result_matches(file_info, mutation_result, "original_dna_sequence", dna_sequence)
    mutation_stats = mutation_result["stats"] if mutation_available else None

    try:
        report = backend_service.analyze_storage(
            file_size_bytes=file_info["size_bytes"],
            dna_length=len(dna_sequence),
            block_size=block_size,
            redundancy_size=redundancy_size,
            mutation_stats=mutation_stats,
        )
    except backend_service.BackendUnavailableError:
        st.warning("⚠️ BioVault backend is unavailable. Falling back to local processing.")
        try:
            report = analyze_storage_efficiency(
                file_size_bytes=file_info["size_bytes"],
                dna_length=len(dna_sequence),
                block_size=block_size,
                redundancy_size=redundancy_size,
                mutation_stats=mutation_stats,
            )
        except StorageAnalysisError as exc:
            st.error(f"❌ Could not compute storage analysis: {exc}")
            return
    except StorageAnalysisError as exc:
        st.error(f"❌ Could not compute storage analysis: {exc}")
        return

    # Cache the latest report, tied to the file/DNA it was computed for,
    # so a rerun (e.g. widget interaction elsewhere) doesn't show stale data.
    st.session_state[ANALYSIS_SESSION_KEY] = {
        "source_filename": file_info["filename"],
        "content_hash": file_info["content_hash"],
        "dna_sequence": dna_sequence,
        "report": report,
    }

    _render_file_and_encoding_summary(file_info, report)
    _render_raw_efficiency(report)
    _render_redundancy_overhead(report)
    _render_mutation_impact(mutation_available, report)
    _render_limitations()


def _render_backend_status_caption() -> None:
    """Show a small status line only when API mode is actually enabled
    -- local mode (the default) shows nothing extra."""
    status = backend_service.backend_status()
    if not status["api_mode"]:
        return
    if status["backend_available"]:
        st.caption(f"🔌 Backend API mode: connected ({status['api_url']})")
    else:
        st.caption(f"🔌 Backend API mode: unavailable ({status['api_url']}) -- will fall back to local processing.")


def _render_redundancy_controls():
    st.subheader("Error-Correction Settings (Phase 6)")
    st.caption("Used to estimate redundancy overhead below -- these do not change any stored encoding/correction results.")
    col1, col2 = st.columns(2)
    with col1:
        block_size = st.slider(
            "Block size", min_value=1, max_value=min(50, MAX_BLOCK_SIZE), value=DEFAULT_BLOCK_SIZE
        )
    with col2:
        redundancy_size = st.slider(
            "Redundancy size", min_value=1, max_value=min(10, MAX_REDUNDANCY_SIZE), value=DEFAULT_REDUNDANCY_SIZE
        )
    return block_size, redundancy_size


def _render_file_and_encoding_summary(file_info: dict, report: dict) -> None:
    st.subheader("A. File & Encoding Summary")
    binary_info = report["binary_info"]
    dna_size_info = report["dna_size_info"]
    capacity_info = report["capacity_info"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Filename", file_info["filename"])
    col2.metric("File Size", format_bytes(report["file_size_bytes"]))
    col3.metric("Binary Bits", f"{binary_info['size_bits']:,} bits")

    col4, col5, col6 = st.columns(3)
    col4.metric("DNA Bases (encoded)", f"{capacity_info['dna_length']:,} bases")
    col5.metric("DNA Bases per Byte", DNA_BASES_PER_BYTE)
    col6.metric("Theoretical Capacity", format_bytes(capacity_info["capacity_bytes"]))

    overhead = report["encoding_overhead"]
    if overhead["difference_bases"] != 0:
        st.warning(
            f"⚠️ Encoded DNA length differs from the expected length by "
            f"{overhead['difference_bases']} base(s) ({overhead['difference_percent']}%)."
        )
    else:
        st.caption("✅ Encoded DNA length exactly matches the expected length for this file size -- no unused or extra capacity.")


def _render_raw_efficiency(report: dict) -> None:
    st.subheader("B. Raw DNA Storage Efficiency")
    data_bits = report["binary_info"]["size_bits"]
    dna_storage_bits = report["capacity_info"]["capacity_bits"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Original Data Bits", f"{data_bits:,} bits")
    col2.metric("DNA Storage Bits", f"{dna_storage_bits:,} bits")
    col3.metric("Raw Efficiency", f"{report['raw_efficiency_percent']}%")

    st.progress(min(int(report["raw_efficiency_percent"]), 100) / 100)

    with st.expander("What does 'raw efficiency' mean here?"):
        st.markdown(
            """
            Each DNA base can hold exactly **2 bits** (from the `00→A,
            01→C, 10→G, 11→T` mapping), so a sequence of *N* bases has a
            storage capacity of *N × 2* bits. Raw efficiency here is:

            ```
            raw efficiency = (original data bits / DNA storage bits) × 100
            ```

            Because file-derived binary data is always a multiple of 8
            bits (and therefore of 2), this scheme never needs padding --
            so raw efficiency is always **exactly 100%** for any file.

            **This is not a claim that DNA storage is more compact than
            the original file.** One DNA base (2 bits of capacity) is
            *smaller* than one byte (8 bits) -- it takes **4 DNA bases**
            to store what 1 byte already stores. This metric only shows
            that none of the DNA sequence's own 2-bit-per-base capacity
            is being wasted by this encoding scheme.
            """
        )


def _render_redundancy_overhead(report: dict) -> None:
    st.subheader("C. Error-Correction Overhead (Phase 6)")
    redundancy = report["redundancy_info"]
    if redundancy is None:
        st.info("Redundancy overhead could not be calculated.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Block Size", redundancy["block_size"])
    col2.metric("Redundancy Size", redundancy["redundancy_size"])
    col3.metric("Number of Blocks", f"{redundancy['num_blocks']:,}")

    col4, col5, col6 = st.columns(3)
    col4.metric("Redundancy Bases Added", f"{redundancy['redundancy_bases']:,}")
    col5.metric("Protected DNA Length", f"{redundancy['protected_length']:,} bases")
    col6.metric("Overhead", f"{redundancy['overhead_percent']}%")

    chart_df = pd.DataFrame(
        {"Bases": ["Original Data", "Redundancy Overhead"], "Count": [redundancy["dna_length"], redundancy["redundancy_bases"]]}
    ).set_index("Bases")
    st.bar_chart(chart_df)

    st.caption(
        "📎 Smaller blocks generally require *more* total redundancy "
        "bases (more blocks means more redundancy copies added overall), "
        "even though smaller blocks also make single-error correction "
        "more reliable -- see the **Error Correction** page for that "
        "trade-off in action."
    )


def _render_mutation_impact(mutation_available: bool, report: dict) -> None:
    st.subheader("D. Mutation Impact (Phase 5)")
    mutation_info = report["mutation_info"]

    if not mutation_available or mutation_info is None:
        st.info(
            "No mutation simulation is currently available.\n\n"
            "Run **Phase 5 (Mutation Simulator)** first to view mutation impact."
        )
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Original DNA Length", f"{mutation_info['original_length']:,} bases")
    col2.metric("Mutated DNA Length", f"{mutation_info['mutated_length']:,} bases")
    col3.metric("Mutation Type", mutation_info["mutation_type"].capitalize())

    col4, col5, col6 = st.columns(3)
    col4.metric("Mutation Rate", f"{mutation_info['mutation_rate']}%")
    col5.metric("Total Simulated Edits", mutation_info["total_edits"])
    col6.metric("Length Difference", f"{mutation_info['length_difference']:+d} bases")

    if mutation_info["length_changed"]:
        st.warning("⚠️ The mutation changed the sequence length (insertion/deletion occurred).")
    else:
        st.caption("ℹ️ The mutation did not change the sequence length (substitution-only, or no edits applied).")


def _render_limitations() -> None:
    st.subheader("E. Limitations")
    st.markdown(
        """
        - This is **not** a real biochemical storage measurement.
        - DNA synthesis and sequencing costs are **not** calculated.
        - Primers, indexes, addressing, and metadata overhead used by
          real DNA storage systems are **not** fully modeled here.
        - Error-correction overhead shown depends entirely on the simple
          block-checksum method from the **Error Correction** page --
          real systems use more sophisticated (and more efficient) codes.
        - Theoretical capacity (2 bits/base) does **not** guarantee
          practical storage capacity, reliability, or cost-effectiveness.
        """
    )
