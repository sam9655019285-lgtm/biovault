"""
UI module: User Guide / Help page.

Renders the content from documentation.py using Streamlit expanders,
headings, and a glossary table. This file only handles presentation --
all wording lives in documentation.py so it can be reviewed/tested
without touching UI code.
"""

import streamlit as st

from app.modules.documentation import (
    get_sections,
    get_quick_start,
    get_common_problems,
    get_glossary,
)

DOCUMENTATION_SESSION_KEY = "documentation_result"


def render_documentation() -> None:
    """Render the User Guide / Help page."""

    st.header("📚 User Guide")
    st.write(
        "A beginner-friendly guide to every BioVault page -- what it does, "
        "how to use it, and what its limitations are. No source-code "
        "reading required."
    )
    st.info(
        "BioVault is an **educational simulation platform**. This guide "
        "describes the platform's actual implemented features only.",
        icon="⚠️",
    )

    st.subheader("🚀 Quick Start")
    st.markdown(get_quick_start())

    st.divider()
    st.subheader("Full Guide")

    sections = get_sections()
    section_titles = [section["title"] for section in sections]

    selected_title = st.selectbox(
        "Jump to a section (or scroll through all sections below)",
        ["Show all sections"] + section_titles,
    )
    st.session_state[DOCUMENTATION_SESSION_KEY] = {"selected_section": selected_title}

    for section in sections:
        if selected_title != "Show all sections" and selected_title != section["title"]:
            continue
        with st.expander(section["title"], expanded=(selected_title == section["title"])):
            st.markdown(section["content"])

    st.divider()
    _render_common_problems()

    st.divider()
    _render_glossary()

    st.divider()
    _render_what_next()


def _render_common_problems() -> None:
    st.subheader("🛠️ Common Problems")
    for item in get_common_problems():
        with st.expander(item["problem"]):
            st.write(item["explanation"])


def _render_glossary() -> None:
    st.subheader("📖 Glossary")
    glossary = get_glossary()
    for term, definition in glossary.items():
        st.markdown(f"**{term}** -- {definition}")


def _render_what_next() -> None:
    st.subheader("➡️ What to Do Next")
    st.markdown(
        """
        - Haven't uploaded a file yet? Start on **File Upload**.
        - Already encoded a file? Try **Mutation Simulator** to see how
          errors affect recovery, then **Error Correction** to see how
          much of that can be fixed.
        - Curious about the numbers? Check **Storage Analysis** and
          **DNA Visualization** for a breakdown.
        - Want to compare stages of your experiment? Visit **Benchmarking**.
        - Want to save your work or reload a sequence? Visit **Export & Import**.
        - Want the full picture of this project? Visit **About BioVault**.
        """
    )
