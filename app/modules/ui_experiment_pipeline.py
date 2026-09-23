"""
UI module: DNA Storage Experiment page.

Combines BioVault's existing modules into one reproducible end-to-end
experiment: encode -> analyze DNA -> analyze storage/capacity -> apply
redundancy -> simulate corruption -> recover -> verify integrity ->
measure performance -> build a research-style report. All orchestration
logic lives in experiment_pipeline.py, which itself only calls existing,
already-tested modules -- this file only handles presentation.

EDUCATIONAL SIMULATION ONLY. Nothing on this page claims real
laboratory DNA storage performance or experimental biological
validation.
"""

import streamlit as st

from app.modules.experiment_pipeline import (
    ExperimentPipelineError,
    EXPERIMENT_STATUS_RECOVERED,
    EXPERIMENT_STATUS_FAILED,
    EXPERIMENT_STATUS_UNABLE_TO_VERIFY,
    EXPERIMENT_STATUS_NOT_AVAILABLE,
    STAGE_NAMES,
    run_experiment,
    generate_experiment_report_text,
)
from app.modules.redundancy_simulation import (
    REDUNDANCY_LEVELS,
    RECOVERY_STRATEGY_MAJORITY,
    RECOVERY_STRATEGY_AGREEMENT,
    RECOVERY_STRATEGY_ERROR_CORRECTION,
    DEFAULT_AGREEMENT_FRACTION,
)
from app.modules.preview_utils import build_preview, preview_caption
from app.modules.result_identity import file_identity_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY

EXPERIMENT_SESSION_KEY = "dna_storage_experiment_result"
HISTORY_SESSION_KEY = "dna_storage_experiment_history"
PREVIEW_LENGTH = 500
MAX_HISTORY = 5

STRATEGY_LABELS = {
    "Existing Error Correction (Phase 6)": RECOVERY_STRATEGY_ERROR_CORRECTION,
    "Majority Vote": RECOVERY_STRATEGY_MAJORITY,
    "Agreement-Based": RECOVERY_STRATEGY_AGREEMENT,
}

STATUS_DISPLAY = {
    EXPERIMENT_STATUS_RECOVERED: ("✅ Successfully Recovered", "success"),
    EXPERIMENT_STATUS_FAILED: ("❌ Recovery Failed", "error"),
    EXPERIMENT_STATUS_UNABLE_TO_VERIFY: ("⚠️ Unable to Verify", "warning"),
    EXPERIMENT_STATUS_NOT_AVAILABLE: ("⚠️ Simulation Completed - Recovery Not Available", "warning"),
}

CORRUPTION_RATE_PRESETS = (0, 1, 5, 10, 20)


def render_experiment_pipeline() -> None:
    """Render the DNA Storage Experiment page."""

    st.header("🧪 DNA Storage Experiment")
    st.write(
        "Run one complete, reproducible end-to-end DNA storage "
        "experiment combining every stage BioVault already implements: "
        "encoding, DNA analysis, storage/capacity analysis, redundancy, "
        "corruption, recovery, integrity verification, and performance "
        "measurement."
    )
    st.warning(
        "This is an **educational software simulation** built entirely "
        "from BioVault's existing modules -- it does not perform real "
        "DNA synthesis or sequencing, and does not constitute "
        "experimental biological validation.",
        icon="⚠️",
    )

    file_info = st.session_state.get(UPLOAD_SESSION_KEY)
    if file_info is None:
        st.info("Please upload a file on **File Upload** first.")
        return

    st.caption(f"Source file: **{file_info['filename']}** ({file_info['size_bytes']:,} bytes)")

    config = _render_configuration()

    if st.button("▶️ Run Experiment", type="primary"):
        _run_experiment_with_progress(file_info, config)

    stored = st.session_state.get(EXPERIMENT_SESSION_KEY)
    if stored is not None and file_identity_matches(file_info, stored):
        _render_summary(stored["result"])
    else:
        st.info("Click **Run Experiment** to generate a result for the current file.")

    _render_history(file_info)


def _render_configuration() -> dict:
    st.subheader("Experiment Configuration")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Corruption**")
        mutation_type = st.selectbox("Corruption type", ("substitution", "insertion", "deletion"))
        mutation_rate = st.select_slider("Corruption rate (%)", options=CORRUPTION_RATE_PRESETS, value=5)
        use_seed = st.checkbox("Use a fixed random seed (reproducible)", value=True)
        seed = st.number_input("Random seed", min_value=0, value=42, step=1) if use_seed else None

    with col2:
        st.markdown("**Redundancy & Recovery**")
        redundancy_label = st.selectbox("Redundancy level", list(REDUNDANCY_LEVELS.keys()))
        extra_copies = REDUNDANCY_LEVELS[redundancy_label]
        strategy_label = st.selectbox("Recovery strategy", list(STRATEGY_LABELS.keys()))
        recovery_strategy = STRATEGY_LABELS[strategy_label]
        agreement_fraction = DEFAULT_AGREEMENT_FRACTION
        if recovery_strategy == RECOVERY_STRATEGY_AGREEMENT:
            agreement_fraction = st.slider("Minimum agreement fraction", 0.1, 1.0, 0.5, 0.05)

    return {
        "mutation_type": mutation_type,
        "mutation_rate": float(mutation_rate),
        "seed": seed,
        "extra_copies": extra_copies,
        "recovery_strategy": recovery_strategy,
        "agreement_fraction": agreement_fraction,
    }


def _run_experiment_with_progress(file_info: dict, config: dict) -> None:
    progress_placeholder = st.empty()
    status_lines = []

    def render_progress(completed_index: int):
        lines = []
        for i, name in enumerate(STAGE_NAMES):
            mark = "✅" if i <= completed_index else "⬜"
            lines.append(f"{i + 1}. {name:<24} {mark}")
        progress_placeholder.code("\n".join(lines), language="text")

    try:
        # The experiment itself runs as one real call (it cannot be
        # meaningfully paused mid-way without re-running stages), so
        # the progress display reflects real, already-completed work
        # once run_experiment() returns -- it is not an artificial
        # animation of work that hasn't happened.
        render_progress(-1)
        result = run_experiment(
            file_info["bytes"],
            file_info["filename"],
            extra_copies=config["extra_copies"],
            mutation_type=config["mutation_type"],
            mutation_rate=config["mutation_rate"],
            seed=config["seed"],
            recovery_strategy=config["recovery_strategy"],
            agreement_fraction=config["agreement_fraction"],
        )
        render_progress(len(STAGE_NAMES) - 1)

        st.session_state[EXPERIMENT_SESSION_KEY] = {
            "source_filename": file_info["filename"],
            "content_hash": file_info["content_hash"],
            "result": result,
        }
        history = st.session_state.get(HISTORY_SESSION_KEY, [])
        history.append(
            {
                "source_filename": file_info["filename"],
                "content_hash": file_info["content_hash"],
                "result": result,
            }
        )
        st.session_state[HISTORY_SESSION_KEY] = history[-MAX_HISTORY:]

        st.success("✅ Experiment complete.")
    except ExperimentPipelineError as exc:
        st.error(f"❌ Could not run experiment: {exc}")


def _render_summary(result: dict) -> None:
    st.divider()
    st.subheader("Experiment Result")

    label, box_kind = STATUS_DISPLAY.get(result["overall_status"], (result["overall_status"], "info"))
    getattr(st, box_kind)(f"**Overall Status: {label}**")

    st.caption(f"Experiment ID: `{result['experiment_id']}`")

    col1, col2, col3 = st.columns(3)
    col1.metric("Original Size", f"{result['file_size_bytes']:,} bytes")
    col2.metric("DNA Length", f"{result['encoding']['dna_length']:,} bases")
    col3.metric("Encoding Overhead", f"{result['encoding']['encoding_overhead_percent']}%")

    if result["dna_analysis"]:
        col4, col5, col6 = st.columns(3)
        col4.metric("GC Content", f"{result['dna_analysis']['gc_percentage']}%")
        col5.metric("AT Content", f"{result['dna_analysis']['at_percentage']}%")
        col6.metric("Longest Homopolymer", result["dna_analysis"]["longest_homopolymer_run"])
        st.caption("📎 GC/homopolymer values are simulation/educational indicators, not proof of biological failure.")

    st.markdown("**Redundancy**")
    col7, col8, col9 = st.columns(3)
    col7.metric("Total Copies", result["redundancy"]["total_copies"])
    col8.metric("Total Stored Bases", f"{result['redundancy']['total_dna_length']:,}")
    col9.metric("Storage Overhead", f"{result['redundancy']['storage_overhead_percent']}%")

    st.markdown("**Corruption**")
    col10, col11, col12 = st.columns(3)
    col10.metric("Type", result["corruption"]["type"].capitalize())
    col11.metric("Rate", f"{result['corruption']['rate_percent']}%")
    col12.metric("Corrupted Copies", result["corruption"]["corrupted_copy_count"])

    st.markdown("**Recovery**")
    col13, col14 = st.columns(2)
    col13.metric("Strategy", result["recovery"]["strategy"].replace("_", " ").title())
    col14.metric("Recovery % (positions resolved)", f"{result['recovery']['recovery_percentage']}%")
    st.caption(
        "📎 Recovery percentage measures positions resolved by voting -- it "
        "does NOT by itself mean the data is correct. Only the integrity "
        "section below (an actual byte comparison) confirms correctness."
    )

    _render_integrity(result["integrity"])
    _render_performance(result["performance"])
    _render_report_download(result)


def _render_integrity(integrity: dict) -> None:
    st.subheader("Integrity Verification")
    col1, col2 = st.columns(2)
    col1.metric("Hashes Match", "✅ Yes" if integrity["hashes_match"] else ("❌ No" if integrity["hashes_match"] is False else "N/A"))
    col2.metric(
        "Exact Byte Recovery",
        "✅ Yes" if integrity["exact_byte_recovery"] is True
        else "❌ No" if integrity["exact_byte_recovery"] is False
        else "N/A",
    )

    with st.expander("SHA-256 hashes"):
        st.markdown("**Original SHA-256:**")
        st.code(integrity["original_hash"] or "N/A", language="text")
        st.markdown("**Recovered SHA-256:**")
        st.code(integrity["recovered_hash"] or "N/A (could not decode recovered data)", language="text")


def _render_performance(performance: dict) -> None:
    st.subheader("Performance (Measured on This Computer)")
    col1, col2 = st.columns(2)
    col1.metric("Encoding Time", f"{performance['encoding_time_seconds']:.6f} s")
    if performance["decoding_time_seconds"] is not None:
        col2.metric("Decoding Time", f"{performance['decoding_time_seconds']:.6f} s")
    st.caption(
        "📎 Timing/memory depend on this computer's hardware, current "
        "workload, and Python version -- never compared to laboratory "
        "DNA storage performance."
    )


def _render_report_download(result: dict) -> None:
    st.subheader("Research-Style Experiment Report")
    report_text = generate_experiment_report_text(result)
    preview = build_preview(report_text, PREVIEW_LENGTH)
    with st.expander("Preview report", expanded=True):
        st.text(preview["preview"])
        if preview["truncated"]:
            st.caption(f"ℹ️ {preview_caption(preview)}")

    st.download_button(
        "⬇️ Download Full Experiment Report (.txt)",
        data=report_text,
        file_name=f"biovault_experiment_{result['experiment_id']}.txt",
        mime="text/plain",
    )


def _render_history(file_info: dict) -> None:
    history = [
        entry for entry in st.session_state.get(HISTORY_SESSION_KEY, [])
        if file_identity_matches(file_info, entry)
    ]
    if not history:
        return

    st.divider()
    st.subheader("Experiment Comparison (This Session)")
    st.caption("Comparing the most recent experiment runs for the current file.")

    rows = []
    for entry in history:
        result = entry["result"]
        rows.append(
            {
                "Experiment ID": result["experiment_id"][:8],
                "Redundancy": result["redundancy"]["total_copies"],
                "Corruption": f"{result['corruption']['type']} @ {result['corruption']['rate_percent']}%",
                "Recovery Strategy": result["recovery"]["strategy"],
                "Recovery %": result["recovery"]["recovery_percentage"],
                "Overall Status": result["overall_status"],
            }
        )

    st.table(rows)
