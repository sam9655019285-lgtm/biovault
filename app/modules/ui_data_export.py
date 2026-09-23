"""
UI module: Export & Import page.

Lets the user download DNA sequences, metadata, analysis CSV, and a
readable text report built from real data already generated on the
previous pages, and lets them import a DNA sequence from a .txt file
for validation/decoding. All export/import/report logic lives in
data_export.py; decoding reuses the existing Phase 4 decoder. This
file only handles presentation.
"""

import json

import streamlit as st

from app.modules.data_export import (
    DataExportError,
    export_dna_text,
    export_metadata_json,
    export_analysis_csv,
    build_report_data,
    generate_text_report,
    import_dna_text,
)
from app.modules.dna_decoder import DNADecodingError, decode_dna_to_file
from app.modules.dna_visualization import count_dna_bases
from app.modules.preview_utils import build_preview, preview_caption
from app.modules.result_identity import file_identity_matches, result_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY
from app.modules.ui_dna_mutation import MUTATION_SESSION_KEY
from app.modules.ui_error_correction import CORRECTION_SESSION_KEY
from app.modules.ui_storage_analysis import ANALYSIS_SESSION_KEY

IMPORTED_DNA_SESSION_KEY = "imported_dna_sequence"
EXPORT_RESULT_SESSION_KEY = "data_export_result"

PREVIEW_LENGTH = 500


def render_data_export() -> None:
    """Render the Export & Import page."""

    st.header("📦 Export & Import")
    st.write(
        "Download DNA sequences, metadata, analysis data, and a readable "
        "project report generated from real data on the previous pages -- "
        "or import a DNA sequence from a text file."
    )
    st.info(
        "This is a **computational data-management feature** for this "
        "simulation project. It does not represent real biological DNA "
        "storage, export, or import.",
        icon="⚠️",
    )

    file_info = st.session_state.get(UPLOAD_SESSION_KEY)
    encoding_result = st.session_state.get(ENCODING_SESSION_KEY)

    encoding_matches = file_identity_matches(file_info, encoding_result)
    dna_sequence = encoding_result["dna_sequence"] if encoding_matches else None

    mutation_result = _get_matching(MUTATION_SESSION_KEY, file_info, "original_dna_sequence", dna_sequence)
    correction_result = _get_matching(CORRECTION_SESSION_KEY, file_info, "original_dna_sequence", dna_sequence)
    analysis_result = _get_matching(ANALYSIS_SESSION_KEY, file_info, "dna_sequence", dna_sequence)

    if not encoding_matches:
        st.info(
            "Upload a file on **File Upload** and generate a DNA sequence "
            "on **DNA Encoding** to unlock DNA/metadata/analysis/report "
            "exports. DNA **import** below works independently."
        )
    else:
        _render_dna_exports(file_info, dna_sequence, mutation_result, correction_result)
        st.divider()
        _render_metadata_export(file_info, encoding_result, mutation_result, correction_result, analysis_result)
        st.divider()
        _render_analysis_csv_export(file_info, encoding_result, mutation_result, correction_result, analysis_result)
        st.divider()
        _render_report_generation(file_info, encoding_result, mutation_result, correction_result, analysis_result)

    st.divider()
    _render_import_section()


def _get_matching(session_key: str, file_info, dna_field: str, dna_sequence):
    """Return a stored result only if it matches the current file identity
    (filename + content hash) and the current DNA sequence."""
    if file_info is None or dna_sequence is None:
        return None
    result = st.session_state.get(session_key)
    if not result_matches(file_info, result, dna_field, dna_sequence):
        return None
    return result


# --- A. Export DNA Sequences --------------------------------------------------

def _render_dna_exports(file_info, dna_sequence, mutation_result, correction_result) -> None:
    st.subheader("A. Export DNA Sequences")

    col1, col2 = st.columns(2)
    with col1:
        try:
            original_text = export_dna_text(dna_sequence)
            st.download_button(
                "⬇️ Download Original DNA (original_dna.txt)",
                data=original_text,
                file_name="original_dna.txt",
                mime="text/plain",
            )
        except DataExportError as exc:
            st.error(f"❌ Could not export original DNA: {exc}")

    with col2:
        if mutation_result is not None:
            try:
                mutated_text = export_dna_text(mutation_result["mutated_dna_sequence"])
                st.download_button(
                    "⬇️ Download Mutated DNA (mutated_dna.txt)",
                    data=mutated_text,
                    file_name="mutated_dna.txt",
                    mime="text/plain",
                )
            except DataExportError as exc:
                st.error(f"❌ Could not export mutated DNA: {exc}")
        else:
            st.caption("ℹ️ Mutated DNA export requires a **Mutation Simulator** result first.")

    col3, col4 = st.columns(2)
    with col3:
        protected_sequence = correction_result.get("protected_sequence") if correction_result else None
        if protected_sequence:
            try:
                protected_text = export_dna_text(protected_sequence)
                st.download_button(
                    "⬇️ Download Protected DNA (protected_dna.txt)",
                    data=protected_text,
                    file_name="protected_dna.txt",
                    mime="text/plain",
                    help="Original DNA + Phase 6 checksum redundancy bases.",
                )
            except DataExportError as exc:
                st.error(f"❌ Could not export protected DNA: {exc}")
        else:
            st.caption("ℹ️ Protected DNA export requires an **Error Correction** result first.")

    with col4:
        corrected_sequence = (correction_result or {}).get("correction", {}).get("corrected_sequence")
        if corrected_sequence:
            try:
                corrected_text = export_dna_text(corrected_sequence)
                st.download_button(
                    "⬇️ Download Corrected DNA (corrected_dna.txt)",
                    data=corrected_text,
                    file_name="corrected_dna.txt",
                    mime="text/plain",
                    help="Redundancy removed after the Phase 6 correction attempt.",
                )
            except DataExportError as exc:
                st.error(f"❌ Could not export corrected DNA: {exc}")
        else:
            st.caption("ℹ️ Corrected DNA export requires a successful **Error Correction** pass first.")


# --- B. Export Metadata ---------------------------------------------------------

def _render_metadata_export(file_info, encoding_result, mutation_result, correction_result, analysis_result) -> None:
    st.subheader("B. Export Metadata")
    metadata = export_metadata_json(file_info, encoding_result, mutation_result, correction_result, analysis_result)
    metadata_json = json.dumps(metadata, indent=2, default=str)

    with st.expander("Preview metadata JSON"):
        st.code(metadata_json, language="json")

    st.download_button(
        "⬇️ Download Metadata JSON (metadata.json)",
        data=metadata_json,
        file_name="metadata.json",
        mime="application/json",
    )


# --- C. Export Analysis ------------------------------------------------------------

def _render_analysis_csv_export(file_info, encoding_result, mutation_result, correction_result, analysis_result) -> None:
    st.subheader("C. Export Analysis")
    csv_text = export_analysis_csv(file_info, encoding_result, mutation_result, correction_result, analysis_result)

    with st.expander("Preview analysis CSV"):
        st.code(csv_text, language="text")

    st.download_button(
        "⬇️ Download Analysis CSV (analysis.csv)",
        data=csv_text,
        file_name="analysis.csv",
        mime="text/csv",
    )


# --- D. Generate Report --------------------------------------------------------------

def _render_report_generation(file_info, encoding_result, mutation_result, correction_result, analysis_result) -> None:
    st.subheader("D. Generate Report")

    if st.button("📄 Generate BioVault Report", type="primary"):
        report_data = build_report_data(file_info, encoding_result, mutation_result, correction_result, analysis_result)
        report_text = generate_text_report(report_data)
        st.session_state[EXPORT_RESULT_SESSION_KEY] = {
            "source_filename": file_info["filename"],
            "content_hash": file_info["content_hash"],
            "dna_sequence": encoding_result["dna_sequence"],
            "report_text": report_text,
        }
        st.success("✅ Report generated.")

    stored = st.session_state.get(EXPORT_RESULT_SESSION_KEY)
    if result_matches(file_info, stored, "dna_sequence", encoding_result["dna_sequence"]):
        with st.expander("Preview report", expanded=True):
            st.text(stored["report_text"])
        st.download_button(
            "⬇️ Download Report (biovault_report.txt)",
            data=stored["report_text"],
            file_name="biovault_report.txt",
            mime="text/plain",
        )


# --- E. Import DNA ------------------------------------------------------------------

def _render_import_section() -> None:
    st.subheader("E. Import DNA")
    st.write(
        "Upload a `.txt` file containing a DNA sequence (A, T, G, C only) "
        "to validate it and, optionally, attempt to decode it back into a file."
    )
    st.caption("Importing does **not** overwrite the original encoded DNA sequence from Phase 3.")

    uploaded = st.file_uploader("Upload DNA sequence (.txt)", type=["txt"], key="dna_import_uploader")

    if uploaded is not None:
        try:
            raw_text = uploaded.getvalue().decode("utf-8", errors="replace")
            imported_sequence = import_dna_text(raw_text)
            st.session_state[IMPORTED_DNA_SESSION_KEY] = imported_sequence
            st.success(f"✅ Imported DNA sequence accepted ({len(imported_sequence):,} bases).")
        except DataExportError as exc:
            st.error(f"❌ Import failed: {exc}")

    imported_sequence = st.session_state.get(IMPORTED_DNA_SESSION_KEY)
    if imported_sequence is None:
        st.info("No DNA sequence has been imported yet.")
        return

    st.markdown("**Imported DNA sequence**")
    imported_preview = build_preview(imported_sequence, PREVIEW_LENGTH)
    st.code(imported_preview["preview"], language="text")
    if imported_preview["truncated"]:
        st.caption(f"ℹ️ {preview_caption(imported_preview)}")

    if st.button("🔍 Validate Imported DNA"):
        counts = count_dna_bases(imported_sequence)
        length_compatible = len(imported_sequence) % 4 == 0
        st.success("✅ Sequence is valid (contains only A, T, G, C).")
        col1, col2, col3 = st.columns(3)
        col1.metric("Sequence Length", f"{len(imported_sequence):,} bases")
        col2.metric("Decoder-Compatible Length", "Yes" if length_compatible else "No")
        col3.metric("Total Bases", counts["total"])
        st.write(f"Base counts: A={counts['A']}, T={counts['T']}, G={counts['G']}, C={counts['C']}")
        if not length_compatible:
            st.warning(
                "⚠️ This sequence's length is not a multiple of 4 bases, so "
                "the Phase 4 decoder will not be able to convert it into "
                "whole bytes without guessing -- decoding will fail."
            )

    if st.button("🔁 Attempt Decode Imported DNA"):
        try:
            decoded = decode_dna_to_file(imported_sequence)
            st.success(f"✅ Decoding succeeded -- recovered {decoded['recovered_size_bytes']:,} byte(s).")
            st.caption(
                "This only confirms the imported DNA decodes into *some* "
                "bytes -- it has not been compared against any specific "
                "original file, so exact-match recovery is not claimed."
            )
            st.download_button(
                "⬇️ Download Recovered Bytes (imported_recovered.bin)",
                data=decoded["recovered_bytes"],
                file_name="imported_recovered.bin",
                mime="application/octet-stream",
            )
        except DNADecodingError as exc:
            st.error(f"❌ Decoding failed: {exc}")


