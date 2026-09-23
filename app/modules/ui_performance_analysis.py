"""
UI module: Performance & Resources page.

Lets the user run BioVault's own encoding/decoding/mutation/error-
correction/storage-analysis pipeline against deterministically
generated small/medium/large test data and see how long it actually
takes and how much memory it actually uses -- on their own computer,
right now. All measurement logic lives in performance_analysis.py;
this file only handles presentation.
"""

import pandas as pd
import streamlit as st

from app.modules.performance_analysis import (
    PerformanceAnalysisError,
    SIZE_PRESETS,
    run_full_benchmark_suite,
)

PERFORMANCE_SESSION_KEY = "performance_analysis_result"


def render_performance_analysis() -> None:
    """Render the Performance & Resources page."""

    st.header("⚙️ Performance & Resources")
    st.write(
        "Run BioVault's real encoding, decoding, mutation, error-correction, "
        "and storage-analysis pipeline against small/medium/large test data, "
        "and see how long each step actually takes and how much memory it "
        "actually uses."
    )
    st.warning(
        "All results on this page are **measured on this computer, right "
        "now** -- they are never fake or hardcoded. Execution time and "
        "memory use depend on your computer's hardware, your Python "
        "version, current system workload, the file size, and the "
        "mutation/error-correction settings used. Do not treat these "
        "numbers as a universal benchmark, and don't expect the exact "
        "same numbers on a different run or a different computer.",
        icon="⚠️",
    )

    preset_label = st.selectbox("Test-size preset", list(SIZE_PRESETS.keys()))
    preset_size_bytes = SIZE_PRESETS[preset_label]
    st.caption(
        f"This will generate **{preset_size_bytes:,} bytes** of deterministic "
        "test data (not a real uploaded file) and run it through the full "
        "pipeline once."
    )

    if st.button("▶️ Run Performance Test", type="primary"):
        _run_test(preset_label, preset_size_bytes)

    stored = st.session_state.get(PERFORMANCE_SESSION_KEY)
    if stored is not None and stored["preset_label"] == preset_label:
        _render_results(stored["result"])
    else:
        st.info("Click **Run Performance Test** to measure the selected preset.")

    with st.expander("Why do results vary between computers?"):
        st.markdown(
            """
            The exact same code can run at very different speeds depending on:

            - **CPU speed and number of cores** available right now
            - **Python version** and how it was installed
            - **Current system workload** (other programs competing for CPU/RAM)
            - **File size** -- larger files mean more bases/bytes to process
            - **Mutation rate / block size** settings -- more edits or smaller
              blocks mean more work per base

            This is exactly why this page always labels its numbers
            *"Measured on this computer"* rather than presenting them as a
            fixed, universal benchmark.
            """
        )


def _run_test(preset_label: str, size_bytes: int) -> None:
    try:
        result = run_full_benchmark_suite(size_bytes)
        st.session_state[PERFORMANCE_SESSION_KEY] = {
            "preset_label": preset_label,
            "result": result,
        }
        st.success("✅ Performance test complete.")
    except PerformanceAnalysisError as exc:
        st.error(f"❌ Could not run performance test: {exc}")


def _render_results(result: dict) -> None:
    st.divider()
    st.subheader("Results")
    st.caption(f"📎 {result['note']} -- input size: {result['input_size_bytes']:,} bytes.")

    rows = []
    for entry in (result["encoding"], result["decoding"], result["mutation"], result["correction"], result["storage"]):
        if entry is None:
            continue
        rows.append(
            {
                "Operation": entry["operation"],
                "Time (seconds)": round(entry["elapsed_seconds"], 6),
                "Peak Memory (KB)": round(entry["peak_memory_bytes"] / 1024, 2),
            }
        )

    table = pd.DataFrame(rows)
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.bar_chart(table.set_index("Operation")["Time (seconds)"])

    st.metric("Total Time For This Run", f"{result['total_elapsed_seconds']:.4f} seconds")

    col1, col2 = st.columns(2)
    col1.metric("Encoded DNA Length", f"{result['encoding']['output_dna_length']:,} bases")
    if result["decoding"] is not None:
        col2.metric("Decoded Back To", f"{result['decoding']['output_size_bytes']:,} bytes")
    else:
        col2.metric("Decoded Back To", "N/A (empty input)")

    if result["correction"] is not None:
        st.caption(
            "📎 The Error Correction measurement times a full "
            "add-redundancy → detect → correct pass with **no simulated "
            "errors introduced**, so it reflects the method's own "
            "processing overhead in isolation."
        )

    with st.expander("What is 'Peak Memory' measuring?"):
        st.markdown(
            """
            Peak memory is measured with Python's built-in `tracemalloc`
            module, which tracks memory used by Python objects while each
            operation runs. It is an **approximation**:

            - It only sees Python-level memory allocations, not memory used
              by lower-level C code.
            - It reflects memory used *during that specific operation*, not
              your whole application's memory footprint.

            It is still useful for seeing the general pattern that larger
            files require proportionally more memory to process.
            """
        )
