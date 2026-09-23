"""
UI module: DNA Encoding page.

Lets the user take the file they already uploaded (File Upload page)
and encode it into a simulated DNA base sequence, using the pipeline
in dna_encoder.py. Displays previews, statistics, and a base-count
chart. All actual encoding logic lives in dna_encoder.py -- this file
only handles presentation.
"""

import pandas as pd
import streamlit as st

from app.modules.dna_encoder import DNAEncodingError, encode_file_to_dna
from app.modules.preview_utils import build_preview, preview_caption
from app.modules.result_identity import file_identity_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.services import backend_service

# Key used to store the DNA encoding result dict in session state.
ENCODING_SESSION_KEY = "dna_encoding_result"

# How many characters of the binary string / DNA sequence to show
# in the on-page preview (the full data is still available via stats
# and, later, for download/decoding).
PREVIEW_LENGTH = 500


def render_dna_encoding() -> None:
    """Render the DNA Encoding page."""

    st.header("🧬 DNA Encoding")
    st.write(
        "Convert your uploaded file into binary, then encode that binary "
        "into a simulated DNA base sequence (A, T, G, C)."
    )
    st.warning(
        "This is a **software simulation** of DNA data encoding for "
        "educational purposes. No real DNA is synthesized or processed.",
        icon="⚠️",
    )

    file_info = st.session_state.get(UPLOAD_SESSION_KEY)
    if file_info is None:
        st.info("Please upload a file on the **File Upload** page first.")
        return

    _render_backend_status_caption()
    _render_source_file_summary(file_info)

    if st.button("🔬 Encode to DNA", type="primary"):
        _run_encoding(file_info)

    result = st.session_state.get(ENCODING_SESSION_KEY)
    if result is not None and file_identity_matches(file_info, result):
        _render_encoding_result(result)


def _render_source_file_summary(file_info: dict) -> None:
    st.subheader("Source File")
    col1, col2 = st.columns(2)
    col1.metric("Filename", file_info["filename"])
    col2.metric("Size", f"{file_info['size_bytes']:,} bytes ({file_info['size_kb']} KB)")


def _render_backend_status_caption() -> None:
    """Show a small status line only when API mode is actually enabled
    -- local mode (the default) shows nothing extra, preserving the
    existing UI exactly."""
    status = backend_service.backend_status()
    if not status["api_mode"]:
        return
    if status["backend_available"]:
        st.caption(f"🔌 Backend API mode: connected ({status['api_url']})")
    else:
        st.caption(f"🔌 Backend API mode: unavailable ({status['api_url']}) -- will fall back to local processing.")


def _run_encoding(file_info: dict) -> None:
    """Run the encoding pipeline (locally, or via the backend API when
    BIOVAULT_USE_API is enabled) and store the result in session state."""
    try:
        result = backend_service.encode(file_info["bytes"])
    except backend_service.BackendUnavailableError:
        st.warning("⚠️ BioVault backend is unavailable. Falling back to local processing.")
        try:
            result = encode_file_to_dna(file_info["bytes"])
        except DNAEncodingError as exc:
            st.error(f"❌ Encoding failed: {exc}")
            return
        except Exception as exc:  # noqa: BLE001 -- never crash the page
            st.error(f"❌ An unexpected error occurred while encoding: {exc}")
            return
    except DNAEncodingError as exc:
        st.error(f"❌ Encoding failed: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 -- never crash the page
        st.error(f"❌ An unexpected error occurred while encoding: {exc}")
        return

    result["source_filename"] = file_info["filename"]
    result["content_hash"] = file_info["content_hash"]
    st.session_state[ENCODING_SESSION_KEY] = result
    st.success("✅ File successfully encoded into a DNA sequence.")


def _render_encoding_result(result: dict) -> None:
    st.divider()
    st.subheader("Encoding Statistics")

    bases_per_byte = 4  # 8 bits / 2 bits-per-base, always exact for byte data
    theoretical_note = (
        "Estimated assuming 1 DNA base can theoretically store 2 bits of "
        "information (this educational scheme's mapping)."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Original File Size", f"{result['original_size_bytes']:,} bytes")
    col2.metric("Binary Length", f"{result['binary_length_bits']:,} bits")
    col3.metric("DNA Sequence Length", f"{result['dna_length']:,} bases")

    col4, col5 = st.columns(2)
    col4.metric("Bits per DNA Base", result["bits_per_base"])
    col5.metric("Bases per Byte", bases_per_byte)

    st.caption(f"📎 {theoretical_note}")

    st.subheader("Base Composition")
    counts = result["base_counts"]
    chart_df = pd.DataFrame(
        {"Base": list(counts.keys()), "Count": list(counts.values())}
    ).set_index("Base")
    st.bar_chart(chart_df)

    st.subheader("Sequence Preview")
    st.markdown("**Binary representation** (first 500 bits):")
    binary_preview = build_preview(result["binary_str"], PREVIEW_LENGTH)
    st.code(binary_preview["preview"], language="text")
    if binary_preview["truncated"]:
        st.caption(f"ℹ️ {preview_caption(binary_preview)}")

    st.markdown("**DNA sequence** (first 500 bases):")
    dna_preview = build_preview(result["dna_sequence"], PREVIEW_LENGTH)
    st.code(dna_preview["preview"], language="text")
    if dna_preview["truncated"]:
        st.caption(f"ℹ️ {preview_caption(dna_preview)}")

    with st.expander("Encoding scheme & full sequence details"):
        st.markdown(
            """
            **2-bit encoding scheme used:**

            | Bits | Base |
            |------|------|
            | 00   | A    |
            | 01   | C    |
            | 10   | G    |
            | 11   | T    |

            Each byte (8 bits) of the file is split into four 2-bit
            chunks, and each chunk is mapped to one DNA base — so every
            byte always becomes exactly 4 bases, with no bits ever
            discarded or padded.
            """
        )
        st.write(f"Full binary length: **{result['binary_length_bits']:,} bits**")
        st.write(f"Full DNA sequence length: **{result['dna_length']:,} bases**")
        st.write("Base counts:")
        st.json(counts)


