"""
UI module: DNA Decoding page.

Takes the DNA sequence already generated on the DNA Encoding page
(Phase 3), decodes it back into bytes using dna_decoder.py, and lets
the user compare the recovered file against the original and download
it. All decoding/comparison logic lives in dna_decoder.py -- this file
only handles presentation.
"""

import streamlit as st

from app.modules.dna_decoder import DNADecodingError, compare_bytes, decode_dna_to_file
from app.modules.preview_utils import build_preview, preview_caption
from app.modules.result_identity import file_identity_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY
from app.services import backend_service

# Key used to store the DNA decoding result dict in session state.
DECODING_SESSION_KEY = "dna_decoding_result"

PREVIEW_LENGTH = 500


def render_dna_decoding() -> None:
    """Render the DNA Decoding page."""

    st.header("🧬 DNA Decoding")
    st.write(
        "Decode the simulated DNA sequence back into binary, then "
        "reconstruct the original file bytes -- demonstrating that no "
        "data was lost during encoding."
    )
    st.warning(
        "This is a **software simulation** of DNA decoding for educational "
        "purposes. No real DNA sequencing is performed.",
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

    # Guard against stale results: only trust the encoding result if it
    # actually belongs to the currently uploaded file (filename AND
    # content hash, so a different file with the same name is caught).
    if not file_identity_matches(file_info, encoding_result):
        st.info(
            "The DNA sequence in memory doesn't match the currently "
            "uploaded file. Please re-encode it on the **DNA Encoding** page."
        )
        return

    _render_backend_status_caption()
    _render_source_summary(file_info, encoding_result)

    if st.button("🔁 Decode DNA to File", type="primary"):
        _run_decoding(encoding_result)

    decoding_result = st.session_state.get(DECODING_SESSION_KEY)
    if decoding_result is not None and _decoding_result_matches(file_info, encoding_result, decoding_result):
        _render_decoding_result(file_info, decoding_result)

    with st.expander("How does DNA decoding work?"):
        st.markdown(
            """
            Decoding simply reverses the encoding scheme from the
            **DNA Encoding** page:

            | Base | Bits |
            |------|------|
            | A    | 00   |
            | C    | 01   |
            | G    | 10   |
            | T    | 11   |

            Every 4 DNA bases (8 bits) are converted back into exactly
            one original byte. If the sequence contains any character
            other than A/T/G/C, or its length doesn't correspond to a
            whole number of bytes, decoding stops and reports an error
            rather than guessing at the missing data.
            """
        )


def _render_source_summary(file_info: dict, encoding_result: dict) -> None:
    st.subheader("Source Data")
    col1, col2, col3 = st.columns(3)
    col1.metric("Source Filename", file_info["filename"])
    col2.metric("Original Size", f"{encoding_result['original_size_bytes']:,} bytes")
    col3.metric("DNA Sequence Length", f"{encoding_result['dna_length']:,} bases")


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


def _run_decoding(encoding_result: dict) -> None:
    """Run the decoding pipeline (locally, or via the backend API when
    BIOVAULT_USE_API is enabled) and store the result in session state."""
    fell_back = False
    try:
        result = backend_service.decode(encoding_result["dna_sequence"])
    except backend_service.BackendUnavailableError:
        st.warning("⚠️ BioVault backend is unavailable. Falling back to local processing.")
        fell_back = True
        try:
            result = decode_dna_to_file(encoding_result["dna_sequence"])
        except DNADecodingError as exc:
            _store_decoding_failure(encoding_result, str(exc))
            st.error(f"❌ Decoding failed: {exc}")
            return
        except Exception as exc:  # noqa: BLE001 -- never crash the page
            _store_decoding_failure(encoding_result, str(exc))
            st.error(f"❌ An unexpected error occurred while decoding: {exc}")
            return
    except DNADecodingError as exc:
        _store_decoding_failure(encoding_result, str(exc))
        st.error(f"❌ Decoding failed: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 -- never crash the page
        _store_decoding_failure(encoding_result, str(exc))
        st.error(f"❌ An unexpected error occurred while decoding: {exc}")
        return

    result["source_filename"] = encoding_result["source_filename"]
    result["content_hash"] = encoding_result["content_hash"]
    result["source_dna_sequence"] = encoding_result["dna_sequence"]
    result["decoding_succeeded"] = True
    st.session_state[DECODING_SESSION_KEY] = result
    if not fell_back:
        st.success("✅ DNA sequence successfully decoded.")


def _store_decoding_failure(encoding_result: dict, error_message: str) -> None:
    st.session_state[DECODING_SESSION_KEY] = {
        "source_filename": encoding_result["source_filename"],
        "content_hash": encoding_result["content_hash"],
        "source_dna_sequence": encoding_result["dna_sequence"],
        "decoding_succeeded": False,
        "error_message": error_message,
    }


def _decoding_result_matches(file_info: dict, encoding_result: dict, decoding_result: dict) -> bool:
    """Return True only if a stored decoding result still belongs to the
    currently uploaded file (filename AND content hash) AND its
    currently encoded DNA sequence.

    Checking the filename alone is not enough: if the user re-encodes
    (producing a new DNA sequence for the same filename) without
    re-running decoding, a stale decoding result from the previous
    sequence must not be displayed as if it matched the new one. Nor is
    checking DNA sequence alone enough: two different files could
    coincidentally encode to related bytes, so file identity is always
    checked first.
    """
    return (
        file_identity_matches(file_info, decoding_result)
        and decoding_result.get("source_dna_sequence") == encoding_result["dna_sequence"]
    )


def _render_decoding_result(file_info: dict, result: dict) -> None:
    st.divider()

    if not result.get("decoding_succeeded"):
        st.error(
            "Decoding did not complete successfully, so no file can be "
            f"recovered or downloaded. Reason: {result.get('error_message')}"
        )
        return

    st.subheader("Decoding Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("DNA Sequence Length", f"{result['dna_length']:,} bases")
    col2.metric("Decoded Binary Length", f"{result['binary_length_bits']:,} bits")
    col3.metric("Recovered File Size", f"{result['recovered_size_bytes']:,} bytes")

    st.markdown("**Decoded binary preview** (first 500 bits):")
    binary_preview = build_preview(result["binary_str"], PREVIEW_LENGTH)
    st.code(binary_preview["preview"], language="text")
    if binary_preview["truncated"]:
        st.caption(f"ℹ️ {preview_caption(binary_preview)}")

    # --- Byte-for-byte comparison -----------------------------------
    st.subheader("Recovery Verification")
    original_bytes = file_info["bytes"]
    recovered_bytes = result["recovered_bytes"]
    comparison = compare_bytes(original_bytes, recovered_bytes)

    col1, col2 = st.columns(2)
    col1.metric("Original Size", f"{comparison['original_size_bytes']:,} bytes")
    col2.metric("Recovered Size", f"{comparison['recovered_size_bytes']:,} bytes")

    if comparison["is_identical"]:
        st.success("✅ Exact recovery confirmed: the recovered file is byte-for-byte identical to the original.")
    else:
        st.error(
            f"❌ Recovery mismatch: {comparison['differing_bytes']:,} byte(s) differ "
            "between the original and recovered file."
        )

    with st.expander("Comparison details"):
        st.json(comparison)

    # --- Download ------------------------------------------------------
    st.subheader("Download Recovered File")
    if comparison["is_identical"]:
        st.download_button(
            label="⬇️ Download Recovered File",
            data=recovered_bytes,
            file_name=file_info["filename"],
            mime=file_info.get("mime_type") or "application/octet-stream",
        )
    else:
        st.info("Download is unavailable because exact recovery was not achieved.")


