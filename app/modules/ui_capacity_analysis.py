"""
UI module: DNA Capacity & Storage page.

Lets the user explore DNA information density, convert file sizes into
theoretical DNA lengths, compare BioVault's actual encoding against the
theoretical ideal, see redundancy/error-correction overhead, run an
illustrative conventional-storage comparison and cost estimate, and
view a few large-scale (up to petabyte) examples -- all computed
mathematically, never by allocating giant DNA strings. All calculation
logic lives in capacity_analysis.py; this file only handles
presentation.

EDUCATIONAL MODULE ONLY. Every section is labeled as theoretical,
measured, measured-vs-theoretical, or estimated -- see
capacity_analysis.py's module docstring for the exact definitions.
This page never claims DNA storage is currently cheaper, faster, or
commercially superior to conventional storage.
"""

import pandas as pd
import streamlit as st

from app.modules.capacity_analysis import (
    CapacityAnalysisError,
    BINARY_UNITS,
    DEFAULT_AVERAGE_BASE_WEIGHT_DALTONS,
    theoretical_density_summary,
    calculate_theoretical_dna_requirement,
    compare_actual_to_theoretical,
    calculate_copy_redundancy_overhead,
    calculate_error_correction_overhead,
    estimate_dna_mass,
    compare_to_conventional_storage,
    estimate_cost,
    generate_scale_examples,
)
from app.modules.dna_error_correction import DEFAULT_BLOCK_SIZE, DEFAULT_REDUNDANCY_SIZE
from app.modules.redundancy_simulation import REDUNDANCY_LEVELS
from app.modules.result_identity import file_identity_matches
from app.modules.ui_upload import SESSION_KEY as UPLOAD_SESSION_KEY
from app.modules.ui_dna_encoding import ENCODING_SESSION_KEY


def render_capacity_analysis() -> None:
    """Render the DNA Capacity & Storage page."""

    st.header("💾 DNA Capacity & Storage")
    st.write(
        "Explore how much digital information DNA can theoretically "
        "represent, and how BioVault's actual encoding compares -- plus "
        "illustrative redundancy, storage, and cost comparisons."
    )
    st.warning(
        "This page is an **educational model**. Theoretical DNA density "
        "does **not** equal practical, usable laboratory density -- real "
        "systems must also handle synthesis/sequencing errors, GC-content "
        "and homopolymer constraints, indexing, error correction, and "
        "physical handling. Cost and physical-mass figures are "
        "**illustrative estimates**, not market quotes or measurements.",
        icon="⚠️",
    )

    _render_information_density_section()
    st.divider()
    _render_file_size_calculator_section()
    st.divider()
    _render_actual_encoding_section()
    st.divider()
    _render_redundancy_section()
    st.divider()
    _render_conventional_storage_section()
    st.divider()
    _render_cost_estimator_section()
    st.divider()
    _render_scale_examples_section()
    st.divider()
    _render_physical_mass_section()
    st.divider()
    _render_educational_explanation()


# --- Section 1: DNA Information Density ------------------------------------------

def _render_information_density_section() -> None:
    st.subheader("1. DNA Information Density (Theoretical)")
    density = theoretical_density_summary()

    col1, col2, col3 = st.columns(3)
    col1.metric("Possible Bases", density["possible_bases"])
    col2.metric("Bits per Base", density["bits_per_base"])
    col3.metric("Bytes per Base", density["bytes_per_base"])

    st.caption(
        "📎 4 possible bases = 2² possibilities, therefore log2(4) = **2 bits "
        "per base**. This is the theoretical information capacity of a "
        "four-symbol alphabet, before any real-world biological or coding "
        "constraint -- not a claim that every real DNA-storage system "
        "achieves 2 *useful* bits/base."
    )

    with st.expander("More density units (theoretical)"):
        col1, col2, col3 = st.columns(3)
        col1.metric("MB per Million Bases", density["mb_per_million_bases"])
        col2.metric("GB per Billion Bases", density["gb_per_billion_bases"])
        col3.metric("TB per Trillion Bases", density["tb_per_trillion_bases"])


# --- Section 2: File Size Calculator ----------------------------------------------

def _render_file_size_calculator_section() -> None:
    st.subheader("2. File Size → Theoretical DNA Length Calculator")

    col1, col2 = st.columns(2)
    with col1:
        value = st.number_input("File size", min_value=0.0, value=1.0, step=1.0)
    with col2:
        unit = st.selectbox("Unit (binary: 1 KB = 1024 bytes)", list(BINARY_UNITS.keys()), index=2)

    try:
        result = calculate_theoretical_dna_requirement(value, unit)
    except CapacityAnalysisError as exc:
        st.error(f"❌ {exc}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Size in Bytes", f"{result['bytes']:,.0f}")
    col2.metric("Theoretical DNA Bases", f"{result['theoretical_dna_bases']:,.0f}")
    col3.metric("Storage Multiplier vs. Bytes", "4x bases per byte")

    st.caption(
        "📎 **Theoretical** figure: DNA bases = bytes × 8 bits/byte ÷ 2 "
        "bits/base = bytes × 4. This does not include any redundancy or "
        "error-correction overhead."
    )


# --- Section 3: Actual BioVault Encoding ------------------------------------------

def _render_actual_encoding_section() -> None:
    st.subheader("3. Actual BioVault Encoding vs. Theoretical")

    file_info = st.session_state.get(UPLOAD_SESSION_KEY)
    encoding_result = st.session_state.get(ENCODING_SESSION_KEY)

    if not file_identity_matches(file_info, encoding_result):
        st.info(
            "Upload a file on **File Upload** and generate a DNA sequence "
            "on **DNA Encoding** to compare BioVault's actual encoded "
            "length against the theoretical ideal (or re-encode if the "
            "file was changed)."
        )
        return

    try:
        result = compare_actual_to_theoretical(file_info["size_bytes"], encoding_result["dna_length"])
    except CapacityAnalysisError as exc:
        st.error(f"❌ {exc}")
        return

    st.caption(f"Source file: **{file_info['filename']}** (measured)")

    col1, col2, col3 = st.columns(3)
    col1.metric("Original File Size (measured)", f"{result['file_size_bytes']:,} bytes")
    col2.metric("Theoretical DNA Length", f"{result['theoretical_dna_length']:,} bases")
    col3.metric("Actual DNA Length (measured)", f"{result['actual_dna_length']:,} bases")

    col4, col5, col6 = st.columns(3)
    col4.metric("Additional Bases", f"{result['additional_bases']:,}")
    col5.metric("Encoding Overhead", f"{result['encoding_overhead_percent']}%")
    col6.metric("Effective Bits/Base (measured)", result["effective_bits_per_base"])

    if result["additional_bases"] == 0:
        st.success(
            "✅ BioVault's actual encoding exactly matches the theoretical "
            "2-bits-per-base ideal for this file (no padding is ever added "
            "by this project's fixed encoding scheme)."
        )
    else:
        st.info("ℹ️ The actual encoded length differs from the theoretical ideal for this file.")


# --- Section 4: Redundancy Calculator ---------------------------------------------

def _render_redundancy_section() -> None:
    st.subheader("4. Redundancy Calculator")

    encoding_result = st.session_state.get(ENCODING_SESSION_KEY)
    file_info = st.session_state.get(UPLOAD_SESSION_KEY)
    has_actual_dna = file_identity_matches(file_info, encoding_result)

    col1, col2 = st.columns(2)
    with col1:
        if has_actual_dna:
            use_actual = st.radio(
                "Base DNA length to use",
                ["Use actual encoded length", "Enter manually"],
                index=0,
            ) == "Use actual encoded length"
        else:
            use_actual = False

        if use_actual:
            dna_length = encoding_result["dna_length"]
            st.caption(f"Using actual encoded DNA length: **{dna_length:,} bases** (measured).")
        else:
            dna_length = int(st.number_input("DNA length (bases)", min_value=0, value=1000, step=1))
    with col2:
        redundancy_label = st.selectbox("Redundancy level (Phase 18)", list(REDUNDANCY_LEVELS.keys()), key="capacity_redundancy_level")
        extra_copies = REDUNDANCY_LEVELS[redundancy_label]

    try:
        copy_overhead = calculate_copy_redundancy_overhead(dna_length, extra_copies)
    except CapacityAnalysisError as exc:
        st.error(f"❌ {exc}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Original DNA Length", f"{copy_overhead['original_dna_length']:,} bases")
    col2.metric("Total DNA Length", f"{copy_overhead['total_dna_length']:,} bases")
    col3.metric("Additional Bases", f"{copy_overhead['additional_bases']:,}")
    st.metric("Storage Overhead (whole-copy redundancy)", f"{copy_overhead['overhead_percent']}%")

    with st.expander("Compare with Phase 6 error-correction overhead"):
        col1, col2 = st.columns(2)
        with col1:
            block_size = st.slider("Block size", 1, 50, DEFAULT_BLOCK_SIZE)
        with col2:
            redundancy_size = st.slider("Redundancy size", 1, 10, DEFAULT_REDUNDANCY_SIZE)
        try:
            ec_overhead = calculate_error_correction_overhead(dna_length, block_size, redundancy_size)
            st.metric("Error-Correction Storage Overhead", f"{ec_overhead['overhead_percent']}%")
            st.caption(
                "📎 This is a **different technique** from whole-copy "
                "redundancy above: a small checksum added to blocks of "
                "ONE sequence, not multiple whole copies. How much of this "
                "overhead is actually 'used' correcting real errors "
                "depends entirely on how many errors occur -- **not "
                "available as a single fixed number** since it depends on "
                "configuration and the actual corruption encountered."
            )
        except CapacityAnalysisError as exc:
            st.error(f"❌ {exc}")


# --- Section 5: Conventional Storage Comparison -----------------------------------

def _render_conventional_storage_section() -> None:
    st.subheader("5. Conventional Digital Storage Comparison (Illustrative)")
    st.caption(
        "Illustrative example sizes only -- not live commercial "
        "capacities or prices. No technology is ranked here."
    )

    rows = compare_to_conventional_storage()
    table = pd.DataFrame(
        [
            {
                "Data Size": row["label"],
                "Digital Size (bytes)": f"{row['digital_size_bytes']:,}",
                "Theoretical DNA Bases": f"{row['theoretical_dna_bases']:,.0f}",
            }
            for row in rows
        ]
    )
    st.dataframe(table, hide_index=True, use_container_width=True)


# --- Section 6: Cost Estimator -----------------------------------------------------

def _render_cost_estimator_section() -> None:
    st.subheader("6. Cost Estimator (Illustrative)")
    st.info(
        "**Illustrative estimate — user assumptions, not a market quote.** "
        "Enter your own assumed costs below; nothing here reflects "
        "current commercial pricing.",
        icon="⚠️",
    )

    col1, col2 = st.columns(2)
    with col1:
        num_bases = st.number_input("Number of DNA bases to cost out", min_value=0, value=1_000_000, step=1000)
        synthesis_cost = st.number_input("Assumed cost per million bases -- synthesis", min_value=0.0, value=0.0, step=1.0)
    with col2:
        sequencing_cost = st.number_input("Assumed cost per million bases -- sequencing", min_value=0.0, value=0.0, step=1.0)
        other_cost = st.number_input("Other assumed flat cost", min_value=0.0, value=0.0, step=1.0)

    try:
        cost_result = estimate_cost(num_bases, synthesis_cost, sequencing_cost, other_cost)
    except CapacityAnalysisError as exc:
        st.error(f"❌ {exc}")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Synthesis (est.)", f"{cost_result['estimated_synthesis_cost']:,.2f}")
    col2.metric("Sequencing (est.)", f"{cost_result['estimated_sequencing_cost']:,.2f}")
    col3.metric("Other (est.)", f"{cost_result['estimated_other_cost']:,.2f}")
    col4.metric("Total Illustrative Estimate", f"{cost_result['total_illustrative_cost']:,.2f}")
    st.caption(f"📎 {cost_result['disclaimer']}")


# --- Section: Scale Examples --------------------------------------------------------

def _render_scale_examples_section() -> None:
    st.subheader("Scale Examples (Theoretical)")
    st.caption(
        "These figures are computed mathematically -- BioVault never "
        "generates an actual petabyte-scale DNA string to produce them."
    )

    extra_copies_for_examples = st.select_slider(
        "Redundancy level to apply to these examples", options=[0, 1, 2, 3], value=0
    )
    rows = generate_scale_examples(extra_copies=extra_copies_for_examples)
    table = pd.DataFrame(
        [
            {
                "Example": row["label"],
                "Digital Size (bytes)": f"{row['digital_size_bytes']:,}",
                "Theoretical DNA Bases": f"{row['theoretical_dna_bases']:,}",
                "Redundancy-Adjusted Bases": f"{row['redundancy_adjusted_bases']:,}",
            }
            for row in rows
        ]
    )
    st.dataframe(table, hide_index=True, use_container_width=True)

    st.markdown("**Chart 1 — DNA Bases Required vs. Data Size (log scale)**")
    chart_df = pd.DataFrame(
        {"Example": [row["label"] for row in rows], "Theoretical DNA Bases": [row["theoretical_dna_bases"] for row in rows]}
    ).set_index("Example")
    st.bar_chart(chart_df)
    st.caption("📎 Values span several orders of magnitude (MB to PB) -- compare relative bar heights rather than exact scale.")


# --- Section 7: Physical DNA Mass Estimate (optional) -----------------------------

def _render_physical_mass_section() -> None:
    st.subheader("7. Physical DNA Mass Estimate (Optional, Educational)")
    st.info(
        "This is an **order-of-magnitude educational model**, not a "
        "measured or laboratory-validated mass. It does not account for "
        "synthesis, purification, sequencing, packaging, or any other "
        "real laboratory process.",
        icon="⚠️",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        num_bases = st.number_input("Number of DNA bases", min_value=0, value=1_000_000, step=1000, key="mass_num_bases")
    with col2:
        copies = st.number_input("Number of copies", min_value=1, value=1, step=1, key="mass_copies")
    with col3:
        weight = st.number_input(
            "Assumed average weight per base (Daltons)",
            min_value=0.01, value=DEFAULT_AVERAGE_BASE_WEIGHT_DALTONS, step=1.0, key="mass_weight",
        )

    try:
        mass_result = estimate_dna_mass(num_bases, copies, weight)
    except CapacityAnalysisError as exc:
        st.error(f"❌ {exc}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Bases (incl. copies)", f"{mass_result['total_bases']:,}")
    col2.metric("Estimated Mass (grams)", f"{mass_result['estimated_mass_grams']:.3e}")
    col3.metric("Estimated Mass (nanograms)", f"{mass_result['estimated_mass_nanograms']:.3f}")

    for assumption in mass_result["assumptions"]:
        st.caption(f"📎 {assumption}")


# --- Educational explanation --------------------------------------------------------

def _render_educational_explanation() -> None:
    with st.expander("📚 Why DNA can (theoretically) store digital information"):
        st.markdown(
            """
            **Why DNA can store digital information:** DNA has four
            possible bases (A, C, G, T). Four possible symbols can
            represent exactly 2 bits of information each (log2(4) = 2),
            the same way two binary digits (00, 01, 10, 11) can represent
            four possibilities.

            **Why practical storage is different:** achieving that
            theoretical 2 bits/base usefully, in a real laboratory
            system, has to deal with:

            - Synthesis errors (writing DNA)
            - Sequencing errors (reading DNA)
            - Random mutations over time
            - GC-content constraints (very high/low GC can be unreliable)
            - Homopolymer runs (long repeated bases are hard to read exactly)
            - Indexing/addressing information (knowing which fragment is which)
            - Error-correction codes (extra redundancy to survive errors)
            - Additional redundancy (multiple copies, as in the
              **Reliability & Redundancy** page)
            - Physical handling, storage, and retrieval time

            **Therefore: theoretical density ≠ practical usable density.**
            Every overhead source above *reduces* how much of that
            theoretical 2 bits/base ends up usable in practice. This page
            always labels its numbers as theoretical, measured, or
            estimated so this distinction stays visible rather than
            implying DNA storage already achieves its theoretical limit
            in the real world.
            """
        )
