"""
UI module: DNA Mutation Simulator page.

Takes the DNA sequence already generated on the DNA Encoding page
(Phase 3), applies a simulated error (substitution/insertion/deletion)
using dna_mutator.py, then attempts to decode the mutated sequence
with the existing Phase 4 decoder to show whether the original file
could still be recovered. All mutation/decoding logic lives in
dna_mutator.py / dna_decoder.py -- this file only handles presentation.
"""

import streamlit as st

from app.modules.dna_mutator import DNAMutationError, mutate_dna
from app.modules.dna_decoder import DNADecodingError, decode_dna_to_file, compare_bytes
from app.modules.preview_utils import build_preview, preview_caption
from app.modules.result_identity import file_identity_matches, result_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY
from app.services import backend_service

# Key used to store the mutation + recovery-attempt result in session state.
MUTATION_SESSION_KEY = "dna_mutation_result"

PREVIEW_LENGTH = 500

MUTATION_TYPE_LABELS = {
    "Substitution": "substitution",
    "Insertion": "insertion",
    "Deletion": "deletion",
}


def render_dna_mutation() -> None:
    """Render the DNA Mutation Simulator page."""

    st.header("🧬 DNA Mutation Simulator")
    st.write(
        "Introduce simulated errors into the DNA sequence generated on the "
        "**DNA Encoding** page, then see whether the original file can "
        "still be recovered after decoding."
    )
    st.warning(
        "This is a **computer simulation** of DNA storage errors. "
        "It is not real biological DNA mutation or laboratory experimentation.",
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
    _render_backend_status_caption()
    _render_source_summary(file_info, original_dna)

    if len(original_dna) == 0:
        st.info("The encoded DNA sequence is empty -- nothing to mutate.")
        return

    mutation_type_label, mutation_rate, seed = _render_controls()

    if st.button("🧪 Simulate Mutation", type="primary"):
        _run_mutation(
            file_info=file_info,
            original_dna=original_dna,
            mutation_type=MUTATION_TYPE_LABELS[mutation_type_label],
            mutation_rate=mutation_rate,
            seed=seed,
        )

    result = st.session_state.get(MUTATION_SESSION_KEY)
    if result_matches(file_info, result, "original_dna_sequence", original_dna):
        _render_result(file_info, result)


def _render_source_summary(file_info: dict, original_dna: str) -> None:
    st.subheader("Source Data")
    col1, col2 = st.columns(2)
    col1.metric("Source Filename", file_info["filename"])
    col2.metric("Original DNA Length", f"{len(original_dna):,} bases")


def _render_controls():
    st.subheader("Mutation Settings")
    col1, col2 = st.columns(2)

    with col1:
        mutation_type_label = st.selectbox(
            "Mutation type",
            list(MUTATION_TYPE_LABELS.keys()),
        )
        mutation_rate = st.slider(
            "Mutation rate (%)",
            min_value=0,
            max_value=100,
            value=5,
            help="Approximate probability, per base (or per gap for insertion), "
            "that an error is introduced.",
        )

    with col2:
        use_seed = st.checkbox("Use a fixed random seed (reproducible results)")
        seed = None
        if use_seed:
            seed = st.number_input("Random seed", min_value=0, value=42, step=1)

    return mutation_type_label, mutation_rate, seed


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


def _run_mutation(file_info: dict, original_dna: str, mutation_type: str, mutation_rate: float, seed) -> None:
    """Run mutation (locally, or via the backend API when
    BIOVAULT_USE_API is enabled), then attempt decoding + recovery
    comparison."""
    used_fallback = False
    try:
        mutation_result = backend_service.mutate(original_dna, mutation_type, mutation_rate, seed)
    except backend_service.BackendUnavailableError:
        st.warning("⚠️ BioVault backend is unavailable. Falling back to local processing.")
        used_fallback = True
        try:
            mutation_result = mutate_dna(original_dna, mutation_type, mutation_rate, seed)
        except DNAMutationError as exc:
            st.error(f"❌ Mutation failed: {exc}")
            return
        except Exception as exc:  # noqa: BLE001 -- never crash the page
            st.error(f"❌ An unexpected error occurred while mutating: {exc}")
            return
    except DNAMutationError as exc:
        st.error(f"❌ Mutation failed: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 -- never crash the page
        st.error(f"❌ An unexpected error occurred while mutating: {exc}")
        return

    mutated_dna = mutation_result["mutated_sequence"]

    # Attempt to decode the mutated DNA using the existing Phase 4
    # decoder (locally or via the backend, matching the mode already
    # chosen above). Mutated DNA is never repaired, padded, or trimmed
    # -- if it can't be decoded as-is, that failure is shown directly.
    decode_succeeded = False
    decode_error = None
    recovered_bytes = None
    comparison = None

    try:
        decoded = decode_dna_to_file(mutated_dna) if used_fallback else backend_service.decode(mutated_dna)
        decode_succeeded = True
        recovered_bytes = decoded["recovered_bytes"]
        comparison = compare_bytes(file_info["bytes"], recovered_bytes)
    except backend_service.BackendUnavailableError:
        # Backend became unreachable between the mutation and decode
        # calls -- fall back locally for this step too, rather than
        # leaving the page without a recovery result.
        try:
            decoded = decode_dna_to_file(mutated_dna)
            decode_succeeded = True
            recovered_bytes = decoded["recovered_bytes"]
            comparison = compare_bytes(file_info["bytes"], recovered_bytes)
        except DNADecodingError as exc:
            decode_error = str(exc)
        except Exception as exc:  # noqa: BLE001
            decode_error = str(exc)
    except DNADecodingError as exc:
        decode_error = str(exc)
    except Exception as exc:  # noqa: BLE001
        decode_error = str(exc)

    result = {
        "source_filename": file_info["filename"],
        "content_hash": file_info["content_hash"],
        "original_dna_sequence": original_dna,
        "mutated_dna_sequence": mutated_dna,
        "mutation_type": mutation_type,
        "mutation_rate": mutation_rate,
        "seed": seed,
        "stats": mutation_result,
        "decode_succeeded": decode_succeeded,
        "decode_error": decode_error,
        "recovered_bytes": recovered_bytes,
        "comparison": comparison,
    }
    st.session_state[MUTATION_SESSION_KEY] = result
    st.success("✅ Mutation simulation complete.")


def _render_result(file_info: dict, result: dict) -> None:
    st.divider()
    stats = result["stats"]

    # --- Mutation statistics --------------------------------------------
    st.subheader("Mutation Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Original DNA Length", f"{stats['original_length']:,} bases")
    col2.metric("Mutated DNA Length", f"{stats['mutated_length']:,} bases")
    col3.metric("Mutation Type", result["mutation_type"].capitalize())

    col4, col5, col6 = st.columns(3)
    col4.metric("Substitutions", stats["substitutions"])
    col5.metric("Insertions", stats["insertions"])
    col6.metric("Deletions", stats["deletions"])

    col7, col8 = st.columns(2)
    col7.metric("Total Simulated Edits", stats["total_edits"])
    col8.metric("Edit Rate", f"{stats['edit_rate_percent']}%")

    st.caption(
        "📎 *Total simulated edits* is counted directly while the mutation "
        "is applied (each substitution, insertion, or deletion is tallied "
        "as it happens) -- it is **not** computed by comparing the original "
        "and mutated sequences position-by-position, since insertions and "
        "deletions shift the alignment between the two and would make such "
        "a comparison meaningless."
    )

    if result["seed"] is not None:
        st.caption(f"🔁 Random seed used: `{result['seed']}` (reproducible).")

    # --- Sequence comparison -----------------------------------------------
    st.subheader("DNA Sequence Comparison")
    st.markdown("**Original DNA sequence** (first 500 bases):")
    original_preview = build_preview(result["original_dna_sequence"], PREVIEW_LENGTH)
    st.code(original_preview["preview"], language="text")
    if original_preview["truncated"]:
        st.caption(f"ℹ️ {preview_caption(original_preview)}")

    st.markdown("**Mutated DNA sequence** (first 500 bases):")
    mutated_preview = build_preview(result["mutated_dna_sequence"], PREVIEW_LENGTH)
    st.code(mutated_preview["preview"], language="text")
    if mutated_preview["truncated"]:
        st.caption(f"ℹ️ {preview_caption(mutated_preview)}")

    with st.expander("Full sequence lengths"):
        st.write(f"Original length: **{len(result['original_dna_sequence']):,} bases**")
        st.write(f"Mutated length: **{len(result['mutated_dna_sequence']):,} bases**")

    # --- Attempted decoding & recovery --------------------------------------
    st.subheader("Attempted Recovery from Mutated DNA")

    if not result["decode_succeeded"]:
        st.error(
            "❌ Exact recovery failed -- the mutated DNA sequence could not "
            f"even be decoded. Reason: {result['decode_error']}"
        )
        st.caption(
            "Insertions and deletions change the sequence length, which can "
            "break it into groups of bits/bases that no longer form whole "
            "bytes -- this is expected and shows why DNA storage errors "
            "matter."
        )
        return

    comparison = result["comparison"]
    col1, col2 = st.columns(2)
    col1.metric("Original File Size", f"{comparison['original_size_bytes']:,} bytes")
    col2.metric("Recovered File Size", f"{comparison['recovered_size_bytes']:,} bytes")

    if comparison["is_identical"]:
        st.success("✅ Exact recovery successful -- the recovered file exactly matches the original.")
    else:
        st.error(
            "❌ Exact recovery failed -- the decoded file differs from the "
            f"original by {comparison['differing_bytes']:,} byte(s)."
        )
        st.caption(
            "Substitution, insertion, or deletion errors in the DNA sequence "
            "can silently corrupt the recovered file even when decoding "
            "itself succeeds without raising an error."
        )

    with st.expander("Comparison details"):
        st.json(comparison)


