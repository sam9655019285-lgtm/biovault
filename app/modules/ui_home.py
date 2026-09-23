"""
UI module: Homepage.

Renders the landing page of BioVault -- project intro, the core
workflow diagram, feature overview cards, and the educational
disclaimer. Later phases will add more UI modules (upload, encoder,
mutation lab, dashboard, etc.) and wire them together from app.py.
"""

import streamlit as st

from app.config import APP_TITLE, APP_SUBTITLE, DISCLAIMER


def render_home() -> None:
    """Render the BioVault homepage."""

    # --- Hero section -----------------------------------------------
    st.markdown(
        f"""
        <div style="
            padding: 2rem 2rem 1.5rem 2rem;
            border-radius: 12px;
            background: linear-gradient(135deg, #0f3d3e 0%, #1a6f6f 60%, #2fa89b 100%);
            color: #f4fffe;
            margin-bottom: 1.5rem;
        ">
            <h1 style="margin-bottom:0.2rem;">🧬 {APP_TITLE}</h1>
            <p style="font-size:1.1rem; opacity:0.9; margin-top:0;">{APP_SUBTITLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(DISCLAIMER, icon="⚠️")

    # --- What this project does --------------------------------------
    st.subheader("What is BioVault?")
    st.write(
        "BioVault is a learning tool that shows, step by step, how digital "
        "files (text, images) can theoretically be represented as a "
        "sequence of DNA bases (A, T, G, C), how random biological-style "
        "errors (mutations) might corrupt that sequence, and how error "
        "correction can help recover the original data."
    )

    # --- Core workflow -------------------------------------------------
    st.subheader("Core Workflow")
    workflow_steps = [
        "📁 Upload File",
        "🔢 Convert to Binary",
        "🧬 Encode Binary → DNA",
        "🔬 Simulate DNA Errors",
        "🔁 Decode DNA → Binary",
        "📄 Reconstruct File",
        "📊 Compare & Analyze",
    ]
    cols = st.columns(len(workflow_steps))
    for col, step in zip(cols, workflow_steps):
        with col:
            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    padding:0.75rem 0.4rem;
                    border-radius:10px;
                    background:#f0f7f6;
                    border:1px solid #d7e9e6;
                    font-size:0.85rem;
                    min-height:70px;
                ">{step}</div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    # --- Feature overview cards -----------------------------------------
    st.subheader("What You'll Find in This App")
    feature_cols = st.columns(3)
    features = [
        ("📁", "File Upload & Binary Encoding",
         "Upload a small text/image file and see it converted into binary, "
         "then encoded into a DNA base sequence."),
        ("🧬", "DNA Mutation Simulator",
         "Introduce simulated substitutions, insertions, and deletions at "
         "an adjustable rate, and inspect exactly what changed."),
        ("🛠️", "Error Correction & Recovery",
         "See a simple, educational redundancy scheme attempt to recover "
         "the original file, with clear accuracy statistics."),
        ("📊", "Dashboard & Visualizations",
         "Track binary size, DNA length, mutation counts, and recovery "
         "accuracy through clear metrics and charts."),
        ("📚", "Educational Section",
         "Learn DNA basics, how digital data maps to DNA, and why DNA is "
         "being explored as an archival storage medium."),
        ("ℹ️", "Project Information",
         "Read about the objectives, technologies, applications, and "
         "limitations of this student project."),
    ]
    for i, (icon, title, desc) in enumerate(features):
        with feature_cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"### {icon} {title}")
                st.write(desc)

    st.divider()
    st.caption(
        "Use the sidebar to navigate between sections as they become "
        "available in later development phases."
    )
