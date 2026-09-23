"""
UI module: DNA Integrity Check page.

Runs BioVault's integrity/corruption-detection checks (dna_integrity.py)
against the currently uploaded file and its encoded DNA sequence, and
offers a small set of clearly-labeled DEMONSTRATION corruption
scenarios (substitution / insertion / deletion / invalid character /
empty / truncated) that always operate on a COPY of the real sequence
-- the original stored DNA is never overwritten. This file only
handles presentation; all integrity logic lives in dna_integrity.py.
"""

import streamlit as st

from app.modules.dna_integrity import (
    DNAIntegrityError,
    STATUS_INVALID,
    STATUS_INCOMPLETE,
    STATUS_CORRUPTED,
    STATUS_UNABLE_TO_VERIFY,
    STATUS_VALID,
    STATUS_RECOVERED,
    build_integrity_report,
)
from app.modules.dna_mutator import mutate_dna
from app.modules.preview_utils import build_preview, preview_caption
from app.modules.result_identity import file_identity_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY

INTEGRITY_SESSION_KEY = "dna_integrity_result"
PREVIEW_LENGTH = 500

STATUS_DISPLAY = {
    STATUS_VALID: ("✅ Valid", "success"),
    STATUS_RECOVERED: ("✅ Successfully Recovered", "success"),
    STATUS_UNABLE_TO_VERIFY: ("ℹ️ Unable to Verify", "info"),
    STATUS_INCOMPLETE: ("⚠️ Incomplete", "warning"),
    STATUS_INVALID: ("❌ Invalid", "error"),
    STATUS_CORRUPTED: ("❌ Corrupted", "error"),
}

DEMO_SCENARIOS = (
    "Valid DNA (no change)",
    "One substituted base",
    "One inserted base",
    "One deleted base",
    "Invalid DNA character",
    "Empty DNA sequence",
    "Truncated DNA sequence",
)


def render_dna_integrity() -> None:
    """Render the DNA Integrity Check page."""

    st.header("🧪 DNA Integrity Check")
    st.write(
        "Check the current DNA sequence for validity, structural "
        "completeness, and (when the original file is available) "
        "confirmed byte-for-byte recovery."
    )
    st.warning(
        "This page never claims **'recovered successfully'** unless the "
        "original and recovered bytes are actually compared and found "
        "identical. Warnings (unusual GC content, long repeated-base "
        "runs) are risk indicators, not proof of corruption.",
        icon="⚠️",
    )

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
    st.caption(f"Source file: **{file_info['filename']}** ({file_info['size_bytes']:,} bytes)")

    if st.button("🔍 Run Integrity Check", type="primary"):
        _run_check(file_info, dna_sequence)

    stored = st.session_state.get(INTEGRITY_SESSION_KEY)
    if stored is not None and file_identity_matches(file_info, stored) and stored.get("scenario") is None:
        _render_report("Current Encoded DNA", stored["report"], dna_sequence)
    else:
        st.info("Click **Run Integrity Check** to check the current DNA sequence.")

    st.divider()
    _render_demo_scenarios(file_info, dna_sequence)
    _render_status_glossary()


def _run_check(file_info, dna_sequence) -> None:
    try:
        report = build_integrity_report(dna_sequence, original_bytes=file_info["bytes"])
        st.session_state[INTEGRITY_SESSION_KEY] = {
            "source_filename": file_info["filename"],
            "content_hash": file_info["content_hash"],
            "scenario": None,
            "report": report,
        }
        st.success("✅ Integrity check complete.")
    except DNAIntegrityError as exc:
        st.error(f"❌ Could not run integrity check: {exc}")


def _render_report(title: str, report: dict, dna_sequence: str = None) -> None:
    st.subheader(title)

    label, box_kind = STATUS_DISPLAY.get(report["status"], (report["status"], "info"))
    getattr(st, box_kind)(f"**Status: {label}**")

    col1, col2, col3 = st.columns(3)
    col1.metric("DNA Length", f"{report['dna_length']:,} bases")
    col2.metric("Invalid Characters", report["invalid_character_count"])
    col3.metric("Can Decode", "Yes" if report["can_decode"] else "No")

    if report["errors"]:
        st.markdown("**Errors:**")
        for error in report["errors"]:
            st.error(f"❌ {error}")

    if report["warnings"]:
        st.markdown("**Warnings (risk indicators, not proof of corruption):**")
        for warning in report["warnings"]:
            st.warning(f"⚠️ {warning}")

    comparison = report["comparison_result"]
    with st.expander("Original vs. Recovered comparison", expanded=comparison is not None):
        if comparison is None:
            st.info(
                "No original file bytes were available for this check, so "
                "recovery could not be confirmed either way (status: "
                "**Unable to Verify** when a recovery check was expected)."
            )
        else:
            col1, col2 = st.columns(2)
            col1.metric("Original Size", f"{comparison['original_length']:,} bytes")
            col2.metric("Recovered Size", f"{comparison['recovered_length']:,} bytes")

            col3, col4 = st.columns(2)
            col3.metric("Differing Bytes", f"{comparison['differing_byte_count']:,}")
            col4.metric(
                "First Difference At",
                comparison["first_difference_index"] if comparison["first_difference_index"] is not None else "N/A",
            )

            st.markdown("**Original SHA-256 hash:**")
            st.code(comparison["original_hash"], language="text")
            st.markdown("**Recovered SHA-256 hash:**")
            st.code(comparison["recovered_hash"], language="text")

            if comparison["is_identical"]:
                st.success("✅ Hashes match -- recovered file is byte-for-byte identical to the original.")
            else:
                st.error("❌ Hashes do not match -- recovered file differs from the original.")

    if dna_sequence:
        # Only the on-screen preview is ever shortened here -- the full
        # sequence used above for every check/decode/comparison is the
        # real, untouched value (see preview_utils.py).
        preview = build_preview(dna_sequence, PREVIEW_LENGTH)
        with st.expander("DNA sequence preview"):
            st.code(preview["preview"], language="text")
            if preview["truncated"]:
                st.caption(f"ℹ️ {preview_caption(preview)}")


def _render_demo_scenarios(file_info, real_dna_sequence: str) -> None:
    st.subheader("🧪 Safe Corruption Scenarios (Demonstration)")
    st.caption(
        "These scenarios always run on a **copy** of the real DNA "
        "sequence for demonstration purposes only. The original stored "
        "DNA sequence used everywhere else in BioVault is never changed."
    )

    scenario = st.selectbox("Choose a scenario", DEMO_SCENARIOS)

    if st.button("▶️ Run Scenario"):
        _run_scenario(file_info, real_dna_sequence, scenario)

    stored = st.session_state.get(INTEGRITY_SESSION_KEY)
    if stored is not None and file_identity_matches(file_info, stored) and stored.get("scenario") == scenario:
        preview = build_preview(stored["demo_sequence"], PREVIEW_LENGTH)
        st.markdown("**Demonstration DNA sequence used for this scenario:**")
        st.code(preview["preview"] or "(empty)", language="text")
        if preview["truncated"]:
            st.caption(f"ℹ️ {preview_caption(preview)}")
        _render_report(f"Scenario Result: {scenario}", stored["report"])

    with st.expander("What do these scenarios teach?"):
        st.markdown(
            """
            - **Substitutions** change one base into another. They *may
              sometimes* be detected (or even corrected) by BioVault's
              Phase 6 error-correction checksum -- but only when
              redundancy was added first, and only for a single,
              unambiguous error per block.
            - **Insertions and deletions** shift every base that comes
              after them, breaking the DNA sequence into the wrong
              4-base groups -- this is why they are especially hard to
              recover from, and why this page reports them as
              **Incomplete** rather than attempting to guess a fix.
            - **A checksum or hash mismatch can tell you something
              changed, but it cannot by itself tell you what the
              original data was** -- recovering from real corruption
              needs redundancy that was added *in advance* (Phase 6),
              not just a way to detect that something is wrong.
            - Error correction in BioVault is limited by design (see the
              **Error Correction** page) -- it is an educational
              demonstration, not a production-grade recovery system.
            """
        )


def _run_scenario(file_info, real_dna_sequence: str, scenario: str) -> None:
    # Always operate on a local copy/derived value -- `real_dna_sequence`
    # itself (and therefore the original session-state encoding result)
    # is never assigned to or mutated below.
    demo_sequence = real_dna_sequence
    original_bytes = file_info["bytes"]

    try:
        if scenario == "Valid DNA (no change)":
            pass  # demo_sequence already equals the real sequence, untouched

        elif scenario == "One substituted base":
            if len(demo_sequence) == 0:
                raise DNAIntegrityError("Cannot substitute a base in an empty sequence.")
            mutation = mutate_dna(demo_sequence, "substitution", mutation_rate=100.0 / len(demo_sequence), seed=1)
            demo_sequence = mutation["mutated_sequence"]

        elif scenario == "One inserted base":
            if len(demo_sequence) == 0:
                demo_sequence = "A"
            else:
                demo_sequence = demo_sequence[:5] + "A" + demo_sequence[5:]

        elif scenario == "One deleted base":
            if len(demo_sequence) == 0:
                raise DNAIntegrityError("Cannot delete a base from an empty sequence.")
            demo_sequence = demo_sequence[:5] + demo_sequence[6:]

        elif scenario == "Invalid DNA character":
            demo_sequence = (demo_sequence[:5] if len(demo_sequence) >= 5 else "") + "Z" + (demo_sequence[6:] if len(demo_sequence) >= 6 else "")

        elif scenario == "Empty DNA sequence":
            demo_sequence = ""

        elif scenario == "Truncated DNA sequence":
            demo_sequence = demo_sequence[: max(0, len(demo_sequence) - 3)]

        report = build_integrity_report(demo_sequence, original_bytes=original_bytes)
        st.session_state[INTEGRITY_SESSION_KEY] = {
            "source_filename": file_info["filename"],
            "content_hash": file_info["content_hash"],
            "scenario": scenario,
            "demo_sequence": demo_sequence,
            "report": report,
        }
        st.success(f"✅ Scenario '{scenario}' complete (demonstration only -- original DNA unchanged).")
    except DNAIntegrityError as exc:
        st.error(f"❌ Could not run scenario: {exc}")


def _render_status_glossary() -> None:
    with st.expander("📚 What do these statuses mean?"):
        st.markdown(
            """
            | Status | Meaning |
            |---|---|
            | ✅ **Valid** | The sequence decodes fine; no recovery claim was requested. |
            | ✅ **Successfully Recovered** | The sequence decodes AND was compared against the original file's bytes, and they are identical. |
            | ℹ️ **Unable to Verify** | The sequence decodes fine, but there is no original file to compare it against. |
            | ⚠️ **Incomplete** | Only valid bases, but the length can't be split into whole bytes (a sign of an insertion or deletion). |
            | ❌ **Invalid** | The sequence is empty, or contains characters other than A/T/G/C. |
            | ❌ **Corrupted** | The sequence decodes, but doesn't match the original file it should recover -- or decoding failed unexpectedly. |

            **Why hashes detect changes but don't repair data:** a
            SHA-256 hash is extremely sensitive to any change -- even
            one differing byte produces a completely different hash --
            so it's an excellent way to detect that something changed.
            But a hash is a one-way summary: it cannot be used to figure
            out *what* the original data was. Only redundancy added
            *before* corruption happens (like BioVault's Phase 6 error
            correction) has any chance of recovering lost information.

            **Why integrity checks matter for DNA data storage:** real
            DNA storage/retrieval involves physical processes (synthesis,
            storage, sequencing) that can introduce errors. Being able to
            clearly tell "this is definitely fine," "this is definitely
            broken," and "I genuinely can't tell" apart -- instead of
            guessing -- is essential for trusting any storage system.
            """
        )
