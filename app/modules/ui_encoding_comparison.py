"""
UI module: Encoding Model Comparison page.

Lets the user compare BioVault's real, default encoding (Model A)
against three clearly labeled educational models (B, C, D) that
illustrate ideas real DNA-storage research cares about -- GC balance
and homopolymer (repeated-base) runs -- using the file already
uploaded and encoded on earlier pages. All model logic lives in
encoding_models.py; this file only handles presentation.

IMPORTANT: this page never feeds Model B/C/D output into the real
decode pipeline. Only Model A (the actual, unmodified encoder/decoder)
is ever reversible here.
"""

import pandas as pd
import streamlit as st

from app.modules.encoding_models import (
    EncodingModelError,
    DEFAULT_HOMOPOLYMER_THRESHOLD,
    DEFAULT_GC_BLOCK_SIZE,
    run_model_comparison,
)
from app.modules.preview_utils import build_preview, preview_caption
from app.modules.result_identity import file_identity_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY

COMPARISON_SESSION_KEY = "encoding_model_comparison_result"
PREVIEW_LENGTH = 500

MODEL_LABELS = {
    "A": "Model A -- Basic Binary-to-DNA (default, reversible)",
    "B": "Model B -- GC-Balanced (simulated, analysis-only)",
    "C": "Model C -- Homopolymer Analysis (analysis-only)",
    "D": "Model D -- GC-Content Analysis (analysis-only)",
}

CATEGORY_BADGES = {
    "reversible": "🟢 Reversible",
    "analysis-only": "🔎 Analysis-only",
}


def render_encoding_comparison() -> None:
    """Render the Encoding Model Comparison page."""

    st.header("🧬 Encoding Model Comparison")
    st.write(
        "Compare BioVault's real, default DNA encoding against a few "
        "clearly labeled **educational, simulated** alternatives that "
        "illustrate ideas real DNA-storage research cares about."
    )
    st.warning(
        "Only **Model A** is BioVault's real, reversible encoding -- it "
        "is the exact same encoder/decoder used everywhere else in the "
        "app. Models B, C, and D are **simulated / analysis-only**: they "
        "are never used to recover a file, and none of them replace or "
        "modify the real pipeline.",
        icon="⚠️",
    )

    file_info = st.session_state.get(UPLOAD_SESSION_KEY)
    encoding_result = st.session_state.get(ENCODING_SESSION_KEY)

    # Same identity guard used everywhere else in the app: filename AND
    # content hash must match, so a different file with the same name
    # can never be mistaken for the one this comparison should use.
    if not file_identity_matches(file_info, encoding_result):
        st.info(
            "Please upload a file on **File Upload** and generate a DNA "
            "sequence on **DNA Encoding** first (or re-encode it if the "
            "file was changed)."
        )
        return

    data = file_info["bytes"]
    st.caption(f"Source file: **{file_info['filename']}** ({file_info['size_bytes']:,} bytes)")

    selected_models = _render_model_selection()
    homopolymer_threshold, gc_block_size = _render_settings()

    if st.button("🔬 Run Comparison", type="primary"):
        _run_comparison(file_info, data, selected_models, homopolymer_threshold, gc_block_size)

    stored = st.session_state.get(COMPARISON_SESSION_KEY)
    if stored is not None and file_identity_matches(file_info, stored):
        _render_results(stored["result"])
    else:
        st.info("Click **Run Comparison** to generate results for the current file.")

    _render_educational_explanations()


def _render_model_selection():
    st.subheader("Select Models to Compare")
    cols = st.columns(4)
    selected = []
    defaults = {"A": True, "B": True, "C": True, "D": True}
    for col, model_id in zip(cols, ("A", "B", "C", "D")):
        with col:
            if st.checkbox(model_id, value=defaults[model_id], key=f"model_checkbox_{model_id}"):
                selected.append(model_id)
            st.caption(MODEL_LABELS[model_id])

    if not selected:
        st.warning("Select at least one model to compare.")
    return selected


def _render_settings():
    with st.expander("Model settings"):
        col1, col2 = st.columns(2)
        with col1:
            homopolymer_threshold = st.slider(
                "Homopolymer risk threshold (Model C)",
                min_value=2,
                max_value=20,
                value=DEFAULT_HOMOPOLYMER_THRESHOLD,
                help="A run of this many identical bases in a row (or more) is flagged as a risk.",
            )
        with col2:
            gc_block_size = st.slider(
                "GC-balancing block size, in bases (Model B)",
                min_value=1,
                max_value=20,
                value=DEFAULT_GC_BLOCK_SIZE,
                help="How many bases' worth of bits Model B considers at a time when choosing a table.",
            )
    return homopolymer_threshold, gc_block_size


def _run_comparison(file_info, data, selected_models, homopolymer_threshold, gc_block_size) -> None:
    if not selected_models:
        return
    try:
        result = run_model_comparison(
            data,
            selected_models=selected_models,
            homopolymer_threshold=homopolymer_threshold,
            gc_block_size=gc_block_size,
        )
        st.session_state[COMPARISON_SESSION_KEY] = {
            "source_filename": file_info["filename"],
            "content_hash": file_info["content_hash"],
            "result": result,
        }
        st.success("✅ Comparison complete.")
    except EncodingModelError as exc:
        st.error(f"❌ Could not run comparison: {exc}")


def _render_results(result: dict) -> None:
    st.divider()
    models = {model_id: model for model_id, model in result["models"].items() if model is not None}

    if not models:
        st.info(
            "No model results are available for this input (an empty "
            "file has no DNA sequence for Models B/C/D to analyze)."
        )
        return

    st.subheader("Comparison Table")
    table_rows = []
    for model_id, model in models.items():
        table_rows.append(
            {
                "Model": model["model_name"],
                "Category": CATEGORY_BADGES.get(model["model_category"], model["model_category"]),
                "DNA Length (bases)": model["dna_length"],
                "GC %": model["gc_percentage"],
                "AT %": model["at_percentage"],
                "Longest Homopolymer Run": model["longest_homopolymer_run"],
                "Recovery Confirmed": (
                    "✅ Yes" if model["recovery_confirmed"] is True
                    else "N/A -- analysis-only" if model["recovery_confirmed"] is None
                    else "❌ No"
                ),
            }
        )
    st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True)

    st.caption(
        "📎 'Storage size estimate' figures for Models B/C/D describe a "
        "**simulated/analysis** sequence, not real storage BioVault "
        "actually writes anywhere -- only Model A's figures come from a "
        "sequence that is genuinely stored and decodable."
    )

    _render_charts(models)
    _render_model_details(models)


def _render_charts(models: dict) -> None:
    st.subheader("Visual Comparison")

    labels = [m["model_name"].split(" -- ")[0].split(" - ")[0] for m in models.values()]

    gc_df = pd.DataFrame({"Model": labels, "GC %": [m["gc_percentage"] for m in models.values()]}).set_index("Model")
    at_df = pd.DataFrame({"Model": labels, "AT %": [m["at_percentage"] for m in models.values()]}).set_index("Model")
    length_df = pd.DataFrame(
        {"Model": labels, "DNA Length (bases)": [m["dna_length"] for m in models.values()]}
    ).set_index("Model")
    homopolymer_df = pd.DataFrame(
        {"Model": labels, "Longest Run": [m["longest_homopolymer_run"] for m in models.values()]}
    ).set_index("Model")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**GC % by model**")
        st.bar_chart(gc_df)
    with col2:
        st.markdown("**AT % by model**")
        st.bar_chart(at_df)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**DNA length by model**")
        st.bar_chart(length_df)
    with col4:
        st.markdown("**Longest homopolymer run by model**")
        st.bar_chart(homopolymer_df)


def _render_model_details(models: dict) -> None:
    st.subheader("Model Details, Strengths & Limitations")

    for model_id, model in models.items():
        with st.expander(f"{model['model_name']} -- details"):
            badge = CATEGORY_BADGES.get(model["model_category"], model["model_category"])
            st.markdown(f"**Category:** {badge}")
            st.write(model["explanation"])

            for warning in model["warnings"]:
                st.warning(f"⚠️ {warning}")

            preview = build_preview(model["dna_sequence"], PREVIEW_LENGTH)
            st.markdown("**DNA sequence preview:**")
            st.code(preview["preview"] or "(empty)", language="text")
            if preview["truncated"]:
                st.caption(f"ℹ️ {preview_caption(preview)}")

            col1, col2, col3 = st.columns(3)
            col1.metric("GC Count", model["gc_count"])
            col2.metric("Invalid Characters", model["invalid_character_count"])
            col3.metric(
                "Storage Estimate",
                f"{model['storage_size_estimate_bases']:,} bases"
                + (" (estimate)" if model["storage_size_is_estimate"] else ""),
            )


def _render_educational_explanations() -> None:
    with st.expander("📚 Why these models exist (educational background)"):
        st.markdown(
            """
            **Why DNA uses A, C, G, and T:** these four bases are the
            natural "alphabet" of real DNA. BioVault reuses them as a
            fixed 4-symbol alphabet for its own simulated encoding
            (2 bits per base), since 4 symbols map neatly onto 2-bit
            chunks (2² = 4).

            **What GC content means:** the percentage of a DNA sequence
            made up of G and C bases (as opposed to A and T). Real
            laboratory DNA synthesis and sequencing tend to work more
            reliably when GC content stays in a moderate, balanced
            range -- sequences that are almost entirely GC or almost
            entirely AT can be harder to synthesize/read accurately.

            **Why balanced GC content can be useful:** it's one of
            several practical constraints real DNA-storage systems
            design around, alongside avoiding long repeated runs
            (below) and other structural patterns. BioVault's Model B
            is a simplified demonstration of *one* possible strategy
            for nudging GC content toward 50%, nothing more.

            **What homopolymers are:** a "homopolymer run" is the same
            base repeated several times in a row, e.g. `AAAA` or
            `GGGG`. **Why long runs can increase errors:** real DNA
            sequencing machines often work by detecting one base at a
            time; a long run of identical bases can make it harder to
            count exactly how many repeats occurred, which can
            introduce insertion/deletion-style errors. BioVault's
            Model C measures this risk without pretending to fix it.

            **Why an encoding model must be reversible for exact file
            recovery:** to get your original file back, *every* bit of
            information used to make an encoding decision must either
            be implicit in the sequence itself, or stored somewhere
            alongside it. Model A satisfies this (its mapping is fixed
            and always reversible). Models B and C, as implemented
            here, make choices per block that are **not** recorded
            anywhere, so those specific choices cannot be undone --
            that is exactly why they are labeled analysis-only rather
            than reversible.

            **Demonstration vs. laboratory-ready:** every model on this
            page is a simplified teaching tool built for this project.
            None of them have been validated against real DNA synthesis
            or sequencing hardware, and none should be treated as a
            production-ready biological encoding algorithm.
            """
        )
