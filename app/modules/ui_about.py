"""
UI module: About BioVault page.

A short project-information page. This will be expanded in a later
phase (Phase 10 in the project plan) with the full problem statement,
objectives, applications, limitations, and future scope. For now it
gives a beginner-friendly overview to accompany the Phase 1/2 features.
"""

import streamlit as st

from app.config import APP_TITLE, APP_SUBTITLE, DISCLAIMER


def render_about() -> None:
    """Render the About BioVault page."""

    st.header(f"ℹ️ About {APP_TITLE}")
    st.write(f"**{APP_SUBTITLE}**")

    st.warning(DISCLAIMER, icon="⚠️")

    st.subheader("Project Goal")
    st.write(
        "BioVault helps biotechnology and bioinformatics students understand "
        "the concept of DNA-based digital data storage by simulating the "
        "full pipeline in software: converting a file to binary, encoding "
        "that binary into a DNA base sequence, introducing simulated "
        "mutations, and decoding it back."
    )

    st.subheader("Current Progress")
    st.markdown(
        """
        - ✅ **Phase 1** — Project structure and homepage
        - ✅ **Phase 2** — File upload and file information display
        - ✅ **Phase 3** — Binary conversion and binary → DNA encoding
        - ✅ **Phase 4** — DNA → binary decoding and file reconstruction
        - ✅ **Phase 5** — DNA mutation / error simulation
        - ✅ **Phase 6** — Error correction and recovery analysis
        - ✅ **Phase 7** — Storage efficiency & compression analysis
        - ✅ **Phase 8** — DNA data visualization & interactive analytics
        - ✅ **Phase 9** — DNA sequence export, import & report generation
        - ✅ **Phase 10** — DNA storage benchmarking & experiment comparison
        - ✅ **Phase 11** — User guide, help system & interactive documentation
        - ✅ **Phase 12** — Final dashboard, project summary & presentation mode
        """
    )

    st.subheader("Technologies Used")
    st.markdown("- Python\n- Streamlit\n- NumPy / Pandas")
