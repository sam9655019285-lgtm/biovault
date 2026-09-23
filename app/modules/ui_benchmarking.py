"""
UI module: Benchmarking page.

Compares Original / Mutated / Protected / Corrected DNA sequences
using the real results already generated on the previous pages, via
benchmarking.py. This file only handles presentation -- all
calculations live in that module.
"""

import streamlit as st

from app.modules.benchmarking import BenchmarkingError, run_benchmark
from app.modules.result_identity import file_identity_matches, result_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY
from app.modules.ui_dna_mutation import MUTATION_SESSION_KEY
from app.modules.ui_error_correction import CORRECTION_SESSION_KEY

BENCHMARK_SESSION_KEY = "benchmarking_result"


def render_benchmarking() -> None:
    """Render the Benchmarking page."""

    st.header("📊 Benchmarking")
    st.write(
        "Compare the Original, Mutated, Protected, and Corrected DNA "
        "sequences side by side, using the real results already "
        "generated on the previous pages."
    )
    st.info(
        "This benchmark reflects **computational simulation results only** "
        "-- it compares this project's own encoding, mutation, and "
        "error-correction output, not real biological DNA experiments.",
        icon="⚠️",
    )

    file_info = st.session_state.get(UPLOAD_SESSION_KEY)
    encoding_result = st.session_state.get(ENCODING_SESSION_KEY)

    encoding_matches = file_identity_matches(file_info, encoding_result)

    if not encoding_matches:
        st.info(
            "Please upload a file on **File Upload** and generate a DNA "
            "sequence on **DNA Encoding** first."
        )
        return

    dna_sequence = encoding_result["dna_sequence"]
    st.subheader("Current Experiment")
    st.caption(f"Source file: **{file_info['filename']}**")

    mutation_result = _get_matching(MUTATION_SESSION_KEY, file_info, "original_dna_sequence", dna_sequence)
    correction_result = _get_matching(CORRECTION_SESSION_KEY, file_info, "original_dna_sequence", dna_sequence)

    col1, col2 = st.columns(2)
    col1.metric("Mutation Data", "Available" if mutation_result else "Not run yet")
    col2.metric("Error-Correction Data", "Available" if correction_result else "Not run yet")

    if st.button("📊 Calculate / Refresh Benchmark", type="primary"):
        try:
            benchmark = run_benchmark(file_info, encoding_result, mutation_result, correction_result)
            st.session_state[BENCHMARK_SESSION_KEY] = {
                "source_filename": file_info["filename"],
                "content_hash": file_info["content_hash"],
                "dna_sequence": dna_sequence,
                "benchmark": benchmark,
            }
            st.success("✅ Benchmark calculated.")
        except BenchmarkingError as exc:
            st.error(f"❌ Could not calculate benchmark: {exc}")

    stored = st.session_state.get(BENCHMARK_SESSION_KEY)
    if result_matches(file_info, stored, "dna_sequence", dna_sequence):
        _render_benchmark(stored["benchmark"])
    else:
        st.info("Click **Calculate / Refresh Benchmark** to generate results for the current experiment.")


def _get_matching(session_key: str, file_info, dna_field: str, dna_sequence):
    """Return a stored result only if it matches the current file identity
    (filename + content hash) and the current DNA sequence."""
    result = st.session_state.get(session_key)
    if not result_matches(file_info, result, dna_field, dna_sequence):
        return None
    return result


def _render_benchmark(benchmark: dict) -> None:
    original_stats = benchmark["original_stats"]
    mutation_stats = benchmark["mutation_stats"]
    correction_stats = benchmark["correction_stats"]
    storage_stats = benchmark["storage_stats"]
    summary = benchmark["summary"]

    st.subheader("Benchmark Metrics")

    if original_stats:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Original DNA Length", f"{original_stats['dna_length']:,} bases")
        col2.metric("File Size", f"{original_stats['file_size_bytes']:,} bytes")
        col3.metric("Bits Represented", f"{original_stats['bits_represented']:,} bits")
        col4.metric("Bits per Nucleotide", original_stats["bits_per_nucleotide"])

    if mutation_stats:
        st.markdown("**Mutation**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Mutated Length", f"{mutation_stats['mutated_length']:,} bases")
        col2.metric("Substitutions", mutation_stats["substitutions"])
        col3.metric("Insertions", mutation_stats["insertions"])
        col4.metric("Deletions", mutation_stats["deletions"])
        if mutation_stats["mutation_rate"] is not None:
            st.caption(f"Mutation rate used: {mutation_stats['mutation_rate']}%")
    else:
        st.caption("ℹ️ Mutation data is not available. Run **Mutation Simulator** first.")

    if correction_stats:
        st.markdown("**Error Correction**")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Protected Length", correction_stats["protected_length"] if correction_stats["protected_length"] is not None else "Not available")
        col2.metric("Corrected Length", correction_stats["corrected_length"] if correction_stats["corrected_length"] is not None else "Not available")
        col3.metric("Errors Detected", correction_stats["errors_detected"] if correction_stats["errors_detected"] is not None else "Unknown")
        col4.metric("Errors Corrected", correction_stats["errors_corrected"])
        st.caption(f"Uncorrectable errors: {correction_stats['uncorrectable_errors']}")
    else:
        st.caption("ℹ️ Error-correction data is not available. Run **Error Correction** first.")

    if storage_stats:
        st.markdown("**Storage Overhead**")
        col1, col2, col3 = st.columns(3)
        col1.metric("Additional Nucleotides", f"{storage_stats['additional_nucleotides']:,}")
        col2.metric("Overhead", f"{storage_stats['overhead_percent']}%")
        col3.metric("Storage Efficiency", f"{storage_stats['efficiency_percent']}%")
    else:
        st.caption("ℹ️ Storage overhead requires both Original and Protected DNA lengths.")

    st.subheader("Original / Mutated / Protected / Corrected Comparison")
    st.dataframe(benchmark["comparison_table"], hide_index=True, use_container_width=True)

    if benchmark["chart_data"] is not None:
        st.subheader("Sequence Length Chart")
        st.bar_chart(benchmark["chart_data"].set_index("Stage")["Length (bases)"])
    else:
        st.info("Not enough data is available yet to draw a sequence-length chart.")

    _render_interpretation(summary)


def _render_interpretation(summary: dict) -> None:
    st.subheader("Benchmark Interpretation")

    if summary["shortest_stage"] is not None:
        st.write(f"📏 **Shortest sequence:** {summary['shortest_stage']} ({summary['shortest_length']:,} bases)")
    else:
        st.write("📏 Shortest sequence: Not available.")

    if summary["highest_overhead_percent"] is not None:
        st.write(f"📦 **Storage overhead:** {summary['highest_overhead_percent']}% added by redundancy.")
    else:
        st.write("📦 Storage overhead: Not available (requires Error Correction data).")

    if summary["correction_restored_length"] is None:
        st.write("🔁 Whether correction restored the original length: Not available.")
    elif summary["correction_restored_length"]:
        st.write("🔁 ✅ The corrected sequence's length matches the original DNA length.")
    else:
        st.write("🔁 ❌ The corrected sequence's length does **not** match the original DNA length.")

    if summary["recovery_confirmed"]:
        st.success("✅ The available data confirms the error-correction pass reported successful recovery.")
    else:
        st.warning(
            "⚠️ Successful recovery is **not** confirmed by the available data "
            "(either no correction has been run, or it did not report full success)."
        )
