"""
UI module: Reliability & Redundancy page.

Lets the user simulate storing multiple redundant copies of the
current DNA sequence, apply controlled corruption, and attempt
recovery via majority vote, agreement-based voting, or BioVault's
existing Phase 6 error correction -- observing storage overhead,
recovery percentage, and (only when actually confirmed) exact
byte-for-byte recovery. All simulation logic lives in
redundancy_simulation.py; this file only handles presentation.

EDUCATIONAL SIMULATION ONLY -- see the in-page explanations and
documentation.py for the full disclaimer. This page never claims to
predict real laboratory DNA-storage reliability.
"""

import pandas as pd
import streamlit as st

from app.modules.redundancy_simulation import (
    RedundancySimulationError,
    REDUNDANCY_LEVELS,
    RECOVERY_STRATEGY_MAJORITY,
    RECOVERY_STRATEGY_AGREEMENT,
    RECOVERY_STRATEGY_ERROR_CORRECTION,
    DEFAULT_AGREEMENT_FRACTION,
    STATUS_RECOVERED,
    STATUS_PARTIALLY_RECOVERED,
    STATUS_FAILED,
    STATUS_UNABLE_TO_VERIFY,
    run_redundancy_simulation,
    run_reliability_experiment,
)
from app.modules.preview_utils import build_preview, preview_caption
from app.modules.result_identity import file_identity_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY

SIMULATION_SESSION_KEY = "redundancy_simulation_result"
EXPERIMENT_SESSION_KEY = "reliability_experiment_result"
PREVIEW_LENGTH = 500

STRATEGY_LABELS = {
    "Majority Vote": RECOVERY_STRATEGY_MAJORITY,
    "Agreement-Based": RECOVERY_STRATEGY_AGREEMENT,
    "Existing Error Correction (Phase 6)": RECOVERY_STRATEGY_ERROR_CORRECTION,
}

STATUS_DISPLAY = {
    STATUS_RECOVERED: ("✅ Successfully Recovered", "success"),
    STATUS_PARTIALLY_RECOVERED: ("⚠️ Partially Recovered", "warning"),
    STATUS_FAILED: ("❌ Recovery Failed", "error"),
    STATUS_UNABLE_TO_VERIFY: ("⚠️ Unable to Verify", "warning"),
}


def render_redundancy_simulation() -> None:
    """Render the Reliability & Redundancy page."""

    st.header("🧬 Reliability & Redundancy")
    st.write(
        "An **educational simulation** demonstrating a general data-storage "
        "idea: storing additional redundant information can increase the "
        "ability to detect or recover from data loss or corruption."
    )
    st.warning(
        "This is a **demonstration of redundancy and recovery concepts**, "
        "not a claim about real laboratory DNA-storage performance. "
        "BioVault's real encode/decode pipeline remains the source of "
        "truth for actual file recovery -- this page only ever works on "
        "independent copies, never the original stored DNA sequence.",
        icon="⚠️",
    )

    _render_explanation_section()

    file_info = st.session_state.get(UPLOAD_SESSION_KEY)
    encoding_result = st.session_state.get(ENCODING_SESSION_KEY)

    if not file_identity_matches(file_info, encoding_result):
        st.info(
            "Please upload a file on **File Upload** and generate a DNA "
            "sequence on **DNA Encoding** first (or re-encode it if the "
            "file was changed)."
        )
        return

    dna_sequence = encoding_result["dna_sequence"]
    if len(dna_sequence) == 0:
        st.info("The encoded DNA sequence is empty -- nothing to simulate.")
        return

    st.caption(f"Source file: **{file_info['filename']}** ({len(dna_sequence):,} bases encoded)")

    _render_settings_and_run(file_info, dna_sequence)
    _render_stored_result(file_info)

    st.divider()
    _render_reliability_experiment(file_info, dna_sequence)


def _render_explanation_section() -> None:
    with st.expander("📚 What is redundancy, and why does it help?", expanded=False):
        st.markdown(
            """
            **What redundancy means:** storing more than the strict minimum
            amount of information needed, so that if some of it is lost or
            changed, the extra copies can help figure out what the original
            probably was.

            **Why it can help:** if you store 3 copies of the same DNA
            sequence and corruption randomly affects a different position
            in each copy, then at most positions at least 2 of the 3 copies
            will still agree -- comparing them ("majority vote") can often
            recover the original base even though every individual copy has
            *some* errors.

            **Storage overhead:** more copies means more total DNA bases
            stored. Redundancy is always a trade-off between reliability
            and storage cost -- this page always shows both sides.

            **Redundancy vs. error correction:** this page's majority-vote
            and agreement-based strategies store multiple **whole copies**
            of the sequence and compare them. BioVault's existing
            **Error Correction** page instead adds a small **checksum**
            next to blocks of a single sequence. Both are forms of
            redundancy in the general sense, but they work differently,
            cost differently, and fail differently -- this page lets you
            try BioVault's real Phase 6 method here too, for comparison.
            """
        )


def _render_settings_and_run(file_info, dna_sequence: str) -> None:
    st.subheader("Simulation Settings")

    col1, col2 = st.columns(2)
    with col1:
        redundancy_label = st.selectbox("Redundancy level", list(REDUNDANCY_LEVELS.keys()), index=1)
        extra_copies = REDUNDANCY_LEVELS[redundancy_label]
        strategy_label = st.selectbox("Recovery strategy", list(STRATEGY_LABELS.keys()))
        recovery_strategy = STRATEGY_LABELS[strategy_label]

    with col2:
        mutation_type = st.selectbox("Corruption (mutation) type", ("substitution", "insertion", "deletion"))
        mutation_rate = st.slider(
            "Corruption amount (%)", min_value=0, max_value=100, value=10,
            help="Approximate probability, per base, that an error is introduced into each copy.",
        )
        use_seed = st.checkbox("Use a fixed random seed (reproducible results)", value=True)
        seed = st.number_input("Random seed", min_value=0, value=42, step=1) if use_seed else None

    agreement_fraction = DEFAULT_AGREEMENT_FRACTION
    if recovery_strategy == RECOVERY_STRATEGY_AGREEMENT:
        agreement_fraction = st.slider(
            "Minimum agreement fraction", min_value=0.1, max_value=1.0, value=0.5, step=0.05,
            help="Fraction of copies that must agree on a base for that position to be recovered.",
        )

    if extra_copies == 0 and recovery_strategy in (RECOVERY_STRATEGY_MAJORITY, RECOVERY_STRATEGY_AGREEMENT):
        st.caption(
            "ℹ️ With **no redundancy**, there is only one copy -- majority/"
            "agreement voting has nothing to compare against, so every "
            "position is trivially 'resolved' as whatever that one copy "
            "says, correct or not. Watch the **recovery confirmation** "
            "below, not just the recovery percentage."
        )

    overhead_preview_length = len(dna_sequence) * (extra_copies + 1)
    st.caption(
        f"This will simulate **{extra_copies + 1} total cop{'y' if extra_copies == 0 else 'ies'}** "
        f"({overhead_preview_length:,} total bases, before any corruption)."
    )

    if st.button("🧪 Run Redundancy Simulation", type="primary"):
        _run_simulation(file_info, dna_sequence, extra_copies, mutation_type, mutation_rate, seed, recovery_strategy, agreement_fraction)


def _run_simulation(file_info, dna_sequence, extra_copies, mutation_type, mutation_rate, seed, recovery_strategy, agreement_fraction) -> None:
    try:
        result = run_redundancy_simulation(
            dna_sequence,
            original_bytes=file_info["bytes"],
            extra_copies=extra_copies,
            mutation_type=mutation_type,
            mutation_rate=mutation_rate,
            seed=seed,
            recovery_strategy=recovery_strategy,
            agreement_fraction=agreement_fraction,
        )
        st.session_state[SIMULATION_SESSION_KEY] = {
            "source_filename": file_info["filename"],
            "content_hash": file_info["content_hash"],
            "result": result,
        }
        st.success("✅ Simulation complete.")
    except RedundancySimulationError as exc:
        st.error(f"❌ Could not run simulation: {exc}")


def _render_stored_result(file_info) -> None:
    stored = st.session_state.get(SIMULATION_SESSION_KEY)
    if stored is None or not file_identity_matches(file_info, stored):
        st.info("Click **Run Redundancy Simulation** to generate results for the current file.")
        return

    result = stored["result"]
    st.divider()
    st.subheader("Simulation Results")

    col1, col2, col3 = st.columns(3)
    col1.metric("Original DNA Length", f"{result['original_dna_length']:,} bases")
    col2.metric("Total Copies", result["total_copies"])
    col3.metric("Corrupted Copies", result["corrupted_copy_count"])

    col4, col5, col6 = st.columns(3)
    col4.metric("Corruption Type", result["mutation_type"].capitalize())
    col5.metric("Corruption Rate", f"{result['mutation_rate']}%")
    col6.metric("Recovery Strategy", result["recovery_strategy"].replace("_", " ").title())

    overhead = result["storage_overhead"]
    col7, col8, col9 = st.columns(3)
    col7.metric("Total Stored Bases", f"{overhead['total_dna_length']:,}")
    col8.metric("Additional Bases", f"{overhead['additional_bases']:,}")
    col9.metric("Storage Overhead", f"{overhead['overhead_percent']}%")

    st.subheader("Recovery Outcome")
    col10, col11 = st.columns(2)
    col10.metric("Recovery Percentage (positions resolved)", f"{result['recovery_percentage']}%")
    col11.metric(
        "Unresolved Positions",
        result["unresolved_position_count"] if result["unresolved_position_count"] is not None else "N/A",
    )
    st.caption(
        "📎 **Recovery percentage measures how many positions had a "
        "confident vote outcome -- it does NOT by itself mean those "
        "positions are correct.** Only the confirmed status below (based "
        "on an actual byte-for-byte comparison) establishes correctness."
    )

    _render_status(result["status"])
    _render_integrity_section(result)

    if result["recovered_sequence"]:
        preview = build_preview(result["recovered_sequence"], PREVIEW_LENGTH)
        with st.expander("Recovered DNA sequence preview"):
            st.code(preview["preview"], language="text")
            if preview["truncated"]:
                st.caption(f"ℹ️ {preview_caption(preview)}")

    with st.expander("What do the recovery statuses mean?"):
        st.markdown(
            """
            - **✅ Successfully Recovered** -- the recovered bytes were
              actually compared to the original file's bytes and found
              identical.
            - **⚠️ Partially Recovered** -- some positions were resolved,
              but the final recovered data does not exactly match the
              original (or could not even be decoded).
            - **❌ Recovery Failed** -- little or nothing could be
              recovered, often because an insertion/deletion broke the
              alignment needed for majority/agreement voting.
            - **⚠️ Unable to Verify** -- there is no original file available
              to compare against, so correctness cannot be confirmed
              either way.
            """
        )


def _render_status(status: str) -> None:
    label, box_kind = STATUS_DISPLAY.get(status, (status, "info"))
    getattr(st, box_kind)(f"**Status: {label}**")


def _render_integrity_section(result: dict) -> None:
    st.subheader("Integrity Verification")

    col1, col2 = st.columns(2)
    col1.metric("Can Decode Recovered Sequence", "Yes" if result["can_decode"] else "No")
    col2.metric(
        "Exact Byte Recovery",
        "✅ Yes" if result["exact_byte_recovery"] is True
        else "❌ No" if result["exact_byte_recovery"] is False
        else "N/A -- unable to verify",
    )

    with st.expander("SHA-256 hashes", expanded=result["comparison_result"] is not None):
        if result["original_hash"]:
            st.markdown("**Original SHA-256 hash:**")
            st.code(result["original_hash"], language="text")
        else:
            st.info("No original file bytes were available to hash.")

        if result["recovered_hash"]:
            st.markdown("**Recovered SHA-256 hash:**")
            st.code(result["recovered_hash"], language="text")
        else:
            st.info("No recovered bytes were available to hash (decoding did not succeed).")

        comparison = result["comparison_result"]
        if comparison is not None:
            col1, col2 = st.columns(2)
            col1.metric("Differing Bytes", f"{comparison['differing_byte_count']:,}")
            col2.metric(
                "First Difference At",
                comparison["first_difference_index"] if comparison["first_difference_index"] is not None else "N/A",
            )


def _render_reliability_experiment(file_info, dna_sequence: str) -> None:
    st.subheader("📊 Reliability Experiment")
    st.write(
        "Run the simulation automatically across several redundancy levels "
        "and corruption rates, and compare the results."
    )

    col1, col2 = st.columns(2)
    with col1:
        redundancy_levels = st.multiselect(
            "Redundancy levels to compare", options=[0, 1, 2, 3], default=[0, 1, 2, 3],
        )
    with col2:
        corruption_rates = st.multiselect(
            "Corruption rates to compare (%)", options=[0, 5, 10, 20, 30], default=[0, 5, 10, 20],
        )

    experiment_mutation_type = st.selectbox(
        "Corruption type for experiment", ("substitution", "insertion", "deletion"), key="experiment_mutation_type"
    )
    experiment_seed = st.number_input("Experiment random seed", min_value=0, value=7, step=1, key="experiment_seed")

    if st.button("▶️ Run Reliability Experiment"):
        _run_experiment(file_info, dna_sequence, redundancy_levels, corruption_rates, experiment_mutation_type, experiment_seed)

    stored = st.session_state.get(EXPERIMENT_SESSION_KEY)
    if stored is not None and file_identity_matches(file_info, stored):
        _render_experiment_results(stored["results"])


def _run_experiment(file_info, dna_sequence, redundancy_levels, corruption_rates, mutation_type, seed) -> None:
    if not redundancy_levels or not corruption_rates:
        st.warning("Select at least one redundancy level and one corruption rate.")
        return
    try:
        results = run_reliability_experiment(
            dna_sequence,
            original_bytes=file_info["bytes"],
            redundancy_levels=sorted(redundancy_levels),
            corruption_rates=sorted(corruption_rates),
            mutation_type=mutation_type,
            seed=seed,
        )
        st.session_state[EXPERIMENT_SESSION_KEY] = {
            "source_filename": file_info["filename"],
            "content_hash": file_info["content_hash"],
            "results": results,
        }
        st.success("✅ Reliability experiment complete.")
    except RedundancySimulationError as exc:
        st.error(f"❌ Could not run experiment: {exc}")


def _render_experiment_results(results: list) -> None:
    st.markdown("**Results table**")
    table = pd.DataFrame(
        [
            {
                "Redundancy Level": row["redundancy_level"],
                "Total Copies": row["total_copies"],
                "Corruption Rate (%)": row["corruption_rate_percent"],
                "Recovery %": row["recovery_percentage"],
                "Storage Overhead (%)": row["storage_overhead_percent"],
                "Status": row["status"],
            }
            for row in results
        ]
    )
    st.dataframe(table, hide_index=True, use_container_width=True)

    st.markdown("**Chart 1 -- Recovery Percentage vs. Corruption Level**")
    chart_data = table.pivot_table(
        index="Corruption Rate (%)", columns="Redundancy Level", values="Recovery %"
    )
    st.line_chart(chart_data)

    st.markdown("**Chart 2 -- Storage Overhead vs. Redundancy Level**")
    overhead_data = (
        table[["Redundancy Level", "Storage Overhead (%)"]]
        .drop_duplicates()
        .set_index("Redundancy Level")
        .sort_index()
    )
    st.bar_chart(overhead_data)

    st.caption(
        "📎 These figures come directly from running the actual simulation "
        "for each combination -- nothing here is hardcoded. As an "
        "**educational demonstration**, they illustrate a general "
        "trade-off (more redundancy can improve recovery chances at the "
        "cost of more storage), not a prediction of real DNA-storage "
        "performance."
    )
