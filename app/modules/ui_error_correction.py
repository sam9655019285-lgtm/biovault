"""
UI module: Error Correction page.

Adds checksum redundancy to the DNA sequence generated on the DNA
Encoding page (Phase 3), simulates errors using the same settings
chosen on the Mutation Simulator page (Phase 5) when available, then
detects and attempts to correct substitution errors using
dna_error_correction.py. Decoding before/after correction reuses the
existing Phase 4 decoder (dna_decoder.py) -- no second decoder is
created. All correction logic lives in dna_error_correction.py; this
file only handles presentation.
"""

import streamlit as st

from app.modules.dna_error_correction import (
    DNAErrorCorrectionError,
    DEFAULT_BLOCK_SIZE,
    DEFAULT_REDUNDANCY_SIZE,
    MAX_BLOCK_SIZE,
    MAX_REDUNDANCY_SIZE,
    add_redundancy,
    detect_errors,
    correct_substitution_errors,
    remove_redundancy,
)
from app.modules.dna_decoder import DNADecodingError, decode_dna_to_file, compare_bytes
from app.modules.dna_mutator import mutate_dna
from app.modules.preview_utils import build_preview, preview_caption
from app.modules.result_identity import file_identity_matches, result_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY
from app.modules.ui_dna_mutation import MUTATION_SESSION_KEY
from app.services import backend_service

CORRECTION_SESSION_KEY = "dna_error_correction_result"
PREVIEW_LENGTH = 500


def render_error_correction() -> None:
    """Render the Error Correction page."""

    st.header("🛡️ Error Correction")
    st.write(
        "Add simple checksum redundancy to the DNA sequence, detect whether "
        "errors are present, and attempt to correct them before decoding."
    )
    st.warning(
        "This is a **simplified educational error-correction model**. "
        "It cannot correct every type of DNA storage error.",
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

    original_dna = encoding_result["dna_sequence"]

    if len(original_dna) == 0:
        st.info("The encoded DNA sequence is empty -- nothing to protect.")
        return

    _render_backend_status_caption()
    st.subheader("Source Data")
    col1, col2 = st.columns(2)
    col1.metric("Source Filename", file_info["filename"])
    col2.metric("Original DNA Length", f"{len(original_dna):,} bases")

    mutation_result = st.session_state.get(MUTATION_SESSION_KEY)
    mutation_available = result_matches(file_info, mutation_result, "original_dna_sequence", original_dna)

    _render_workflow_explanation(mutation_available, mutation_result)

    block_size, redundancy_size = _render_controls()

    if st.button("🛡️ Apply Error Correction", type="primary"):
        _run_correction(
            file_info=file_info,
            original_dna=original_dna,
            block_size=block_size,
            redundancy_size=redundancy_size,
            mutation_result=mutation_result if mutation_available else None,
        )

    result = st.session_state.get(CORRECTION_SESSION_KEY)
    if result_matches(file_info, result, "original_dna_sequence", original_dna):
        _render_result(file_info, result)


def _render_workflow_explanation(mutation_available: bool, mutation_result) -> None:
    with st.expander("How this page works", expanded=not mutation_available):
        st.markdown(
            """
            **Workflow:** Original DNA → add checksum redundancy → simulate
            errors → detect errors → attempt correction → decode → compare
            to the original file.
            """
        )
        if mutation_available:
            st.info(
                "A DNA sequence from the **Mutation Simulator** page was found. "
                "Because redundancy must be added *before* errors occur, this "
                "page re-applies the **same mutation settings** "
                f"(`{mutation_result['mutation_type']}`, "
                f"{mutation_result['mutation_rate']}% rate, "
                f"seed=`{mutation_result['seed']}`) to a freshly "
                "redundancy-protected copy of the sequence, rather than "
                "reusing that page's already-mutated sequence directly "
                "(which has no redundancy embedded in it)."
            )
        else:
            st.info(
                "No matching result was found on the **Mutation Simulator** "
                "page, so no simulated errors will be applied here -- the "
                "redundancy-protected sequence will be used unchanged, "
                "which should show a successful, error-free correction pass."
            )


def _render_controls():
    st.subheader("Redundancy Settings")
    col1, col2 = st.columns(2)
    with col1:
        block_size = st.slider(
            "Block size (bases per checksum block)",
            min_value=1,
            max_value=min(50, MAX_BLOCK_SIZE),
            value=DEFAULT_BLOCK_SIZE,
            help="Smaller blocks make single-error correction more reliable, "
            "but add more redundancy overhead.",
        )
    with col2:
        redundancy_size = st.slider(
            "Redundancy size (checksum bases per block)",
            min_value=1,
            max_value=min(10, MAX_REDUNDANCY_SIZE),
            value=DEFAULT_REDUNDANCY_SIZE,
            help="Number of times the block's checksum base is repeated.",
        )
    return block_size, redundancy_size


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


def _run_correction(file_info, original_dna, block_size, redundancy_size, mutation_result) -> None:
    """Run the full protect -> (mutate) -> detect -> correct -> decode
    pass, either entirely via the backend API or entirely locally.

    If the backend becomes unavailable partway through an API-mode
    pass, the ENTIRE pass is safely re-run locally from scratch, rather
    than mixing partial API/local results together.
    """
    try:
        result = _perform_correction(file_info, original_dna, block_size, redundancy_size, mutation_result, use_api=True)
    except backend_service.BackendUnavailableError:
        st.warning("⚠️ BioVault backend is unavailable. Falling back to local processing.")
        try:
            result = _perform_correction(file_info, original_dna, block_size, redundancy_size, mutation_result, use_api=False)
        except DNAErrorCorrectionError as exc:
            st.error(f"❌ Error correction failed: {exc}")
            return
        except Exception as exc:  # noqa: BLE001 -- never crash the page
            st.error(f"❌ An unexpected error occurred: {exc}")
            return
    except DNAErrorCorrectionError as exc:
        st.error(f"❌ Error correction failed: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 -- never crash the page
        st.error(f"❌ An unexpected error occurred: {exc}")
        return

    st.session_state[CORRECTION_SESSION_KEY] = result
    st.success("✅ Error correction pass complete.")


def _perform_correction(file_info, original_dna, block_size, redundancy_size, mutation_result, use_api: bool) -> dict:
    if use_api:
        protection = backend_service.protect_dna(original_dna, block_size, redundancy_size)
    else:
        protection = add_redundancy(original_dna, block_size, redundancy_size)
    protected_sequence = protection["protected_sequence"]
    original_length = protection["original_length"]

    if mutation_result is not None:
        if use_api:
            mutated = backend_service.mutate(
                protected_sequence, mutation_result["mutation_type"], mutation_result["mutation_rate"], mutation_result["seed"]
            )
        else:
            mutated = mutate_dna(
                protected_sequence, mutation_result["mutation_type"], mutation_result["mutation_rate"], mutation_result["seed"]
            )
        received_sequence = mutated["mutated_sequence"]
        mutation_applied = True
    else:
        received_sequence = protected_sequence
        mutation_applied = False

    if use_api:
        detection_before = backend_service.detect_dna_errors(original_dna, received_sequence, block_size, redundancy_size)
    else:
        detection_before = detect_errors(received_sequence, block_size, redundancy_size, original_length)

    before_decode = _attempt_decode_and_compare(received_sequence, file_info["bytes"], use_api)

    if use_api:
        correction = backend_service.correct_dna_errors(original_dna, received_sequence, block_size, redundancy_size)
    else:
        correction = correct_substitution_errors(received_sequence, block_size, redundancy_size, original_length)

    after_decode = {"decode_succeeded": False, "decode_error": "Correction did not produce a decodable sequence.", "comparison": None}
    if correction["corrected_sequence"] is not None:
        after_decode = _attempt_decode_and_compare(correction["corrected_sequence"], file_info["bytes"], use_api)

    return {
        "source_filename": file_info["filename"],
        "content_hash": file_info["content_hash"],
        "original_dna_sequence": original_dna,
        "block_size": block_size,
        "redundancy_size": redundancy_size,
        "mutation_applied": mutation_applied,
        "protected_sequence": protected_sequence,
        "received_sequence": received_sequence,
        "detection_before": detection_before,
        "before_decode": before_decode,
        "correction": correction,
        "after_decode": after_decode,
    }


def _attempt_decode_and_compare(dna_sequence: str, original_bytes: bytes, use_api: bool = False) -> dict:
    """Try decoding a DNA sequence with the existing Phase 4 decoder,
    locally or via the backend API. A BackendUnavailableError is
    deliberately propagated (not caught) so the caller's outer handler
    can re-run the entire correction pass locally, instead of mixing a
    partial API result with a partial local one."""
    try:
        decoded = backend_service.decode(dna_sequence) if use_api else decode_dna_to_file(dna_sequence)
        comparison = compare_bytes(original_bytes, decoded["recovered_bytes"])
        return {"decode_succeeded": True, "decode_error": None, "comparison": comparison}
    except backend_service.BackendUnavailableError:
        raise
    except DNADecodingError as exc:
        return {"decode_succeeded": False, "decode_error": str(exc), "comparison": None}
    except Exception as exc:  # noqa: BLE001
        return {"decode_succeeded": False, "decode_error": str(exc), "comparison": None}


def _render_result(file_info: dict, result: dict) -> None:
    st.divider()

    if result["mutation_applied"]:
        st.caption("🧪 Simulated errors (from the Mutation Simulator's settings) were applied before detection.")
    else:
        st.caption("ℹ️ No simulated mutation was applied -- using the redundancy-protected sequence as-is.")

    # --- Before correction ---------------------------------------------
    st.subheader("Before Correction")
    detection = result["detection_before"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Received Sequence Length", f"{len(result['received_sequence']):,} bases")
    col2.metric(
        "Blocks Checked",
        detection["blocks_checked"] if detection["length_matches_expected"] else "N/A",
    )
    col3.metric(
        "Errors Detected",
        detection["errors_detected"] if detection["errors_detected"] is not None else "Unknown",
    )
    st.caption(f"📎 {detection['message']}")

    _render_decode_outcome("Decoding attempt (received sequence, before correction)", result["before_decode"])

    # --- Correction --------------------------------------------------------
    st.subheader("Correction Result")
    correction = result["correction"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Errors Detected", correction["errors_detected"] if correction["errors_detected"] is not None else "Unknown")
    col2.metric("Errors Corrected", correction["errors_corrected"])
    col3.metric("Uncorrectable Errors", correction["uncorrectable_errors"] if correction["uncorrectable_errors"] is not None else "Unknown")

    if correction["correction_success"]:
        st.success(f"✅ {correction['message']}")
    else:
        st.error(f"❌ {correction['message']}")

    # --- After correction -----------------------------------------------------
    st.subheader("After Correction")
    if correction["corrected_sequence"] is not None:
        st.metric("Corrected Sequence Length", f"{len(correction['corrected_sequence']):,} bases")
        _render_decode_outcome("Decoding attempt (corrected sequence)", result["after_decode"])
    else:
        st.info("No corrected sequence is available (structural length mismatch -- see message above).")

    # --- Sequence previews -------------------------------------------------
    with st.expander("Sequence details"):
        st.markdown("**Protected sequence** (original DNA + redundancy, first 500 bases):")
        protected_preview = build_preview(result["protected_sequence"], PREVIEW_LENGTH)
        st.code(protected_preview["preview"], language="text")
        if protected_preview["truncated"]:
            st.caption(f"ℹ️ {preview_caption(protected_preview)}")

        st.markdown("**Received sequence** (after simulated errors, first 500 bases):")
        received_preview = build_preview(result["received_sequence"], PREVIEW_LENGTH)
        st.code(received_preview["preview"], language="text")
        if received_preview["truncated"]:
            st.caption(f"ℹ️ {preview_caption(received_preview)}")

        if correction["corrected_sequence"] is not None:
            st.markdown("**Corrected sequence** (redundancy removed, first 500 bases):")
            corrected_preview = build_preview(correction["corrected_sequence"], PREVIEW_LENGTH)
            st.code(corrected_preview["preview"], language="text")
            if corrected_preview["truncated"]:
                st.caption(f"ℹ️ {preview_caption(corrected_preview)}")

        st.write(f"Block size: **{result['block_size']}**, Redundancy size: **{result['redundancy_size']}**")

    with st.expander("Limitations of this correction method"):
        st.markdown(
            """
            - Only **substitution** errors can potentially be corrected --
              insertions/deletions break the block structure and are only
              reported as a length mismatch.
            - At most **one confidently-identified substitution per block**
              can be fixed. If a block has multiple errors, or the checksum
              coincidentally matches more than one possible fix, the block
              is left uncorrected rather than guessed at.
            - This is a teaching demonstration, not a production-grade or
              biologically accurate DNA error-correction system.
            """
        )


def _render_decode_outcome(title: str, decode_outcome: dict) -> None:
    st.markdown(f"**{title}**")
    if not decode_outcome["decode_succeeded"]:
        st.error(f"❌ Decoding failed: {decode_outcome['decode_error']}")
        return

    comparison = decode_outcome["comparison"]
    col1, col2 = st.columns(2)
    col1.metric("Recovered Size", f"{comparison['recovered_size_bytes']:,} bytes")
    col2.metric("Original Size", f"{comparison['original_size_bytes']:,} bytes")

    if comparison["is_identical"]:
        st.success("✅ Exact recovery successful.")
    else:
        st.error(f"❌ Exact recovery failed -- {comparison['differing_bytes']:,} byte(s) differ.")


