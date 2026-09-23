"""
UI module: Project Showcase page.

The main presentation/demonstration page for college project reviews,
viva voce, seminars, and classroom demos. All static content lives in
showcase_content.py; this file only handles presentation.

ACADEMIC HONESTY: this page repeatedly and explicitly states that
BioVault is a computational educational simulation -- never a claim of
real DNA synthesis, sequencing, physical storage, or laboratory
validation.
"""

import streamlit as st

from app.modules.showcase_content import (
    APP_TITLE,
    APP_SUBTITLE,
    INTRO_TEXT,
    SOFTWARE_SIMULATION_NOTICE,
    PROBLEM_STATEMENT,
    OBJECTIVES,
    WORKFLOW_STAGES,
    ENCODING_EXAMPLE_BINARY,
    ENCODING_EXAMPLE_DNA,
    WHY_FOUR_BASES_TEXT,
    LIVE_DEMO_CHECKLIST,
    DEMO_RECOMMENDATION,
    DEMO_RECOMMENDATION_LABEL,
    DEMO_RESULT_EXPLANATION,
    RECOVERY_PERCENTAGE_TEACHING_POINT,
    SCIENTIFIC_CONCEPTS,
    LIMITATIONS_DOES_NOT,
    LIMITATIONS_STATEMENT,
    ARCHITECTURE_DIAGRAM,
    ARCHITECTURE_KEY_MODULES,
    PROJECT_TIMELINE,
    SLIDE_OUTLINE,
    FUTURE_SCOPE,
    PROJECT_CONCLUSION,
    get_project_statistics,
)


def render_project_showcase() -> None:
    """Render the Project Showcase page."""

    st.title(APP_TITLE)
    st.markdown(f"### {APP_SUBTITLE}")
    st.write(INTRO_TEXT)
    st.warning(f"⚠️ **{SOFTWARE_SIMULATION_NOTICE}**")

    _render_problem_section()
    _render_objectives_section()
    _render_workflow_section()
    _render_encoding_section()
    _render_live_demo_section()
    _render_scientific_concepts_section()
    _render_limitations_section()
    _render_architecture_section()
    _render_timeline_section()
    _render_statistics_section()
    _render_slide_outline_section()
    _render_future_scope_section()
    _render_conclusion_section()


def _render_problem_section() -> None:
    st.header("Problem")
    st.markdown(PROBLEM_STATEMENT)


def _render_objectives_section() -> None:
    st.header("Objectives")
    for i, objective in enumerate(OBJECTIVES, start=1):
        st.write(f"{i}. {objective}")


def _render_workflow_section() -> None:
    st.header("How BioVault Works")
    st.code(" \n     ↓\n".join(WORKFLOW_STAGES), language="text")


def _render_encoding_section() -> None:
    st.header("Core Encoding Explanation")
    st.write("BioVault's actual, fixed 2-bit mapping (see `dna_encoder.py`):")

    col1, col2 = st.columns(2)
    col1.markdown("**00 → A**")
    col1.markdown("**01 → C**")
    col2.markdown("**10 → G**")
    col2.markdown("**11 → T**")

    st.markdown("**Example:**")
    st.code(f"Binary: {ENCODING_EXAMPLE_BINARY}\nDNA:    {ENCODING_EXAMPLE_DNA}", language="text")

    with st.expander("Why does DNA have four bases, and why 2 bits per base?"):
        st.write(WHY_FOUR_BASES_TEXT)


def _render_live_demo_section() -> None:
    st.header("Live Demo")
    st.write("Follow this checklist using the app's other pages -- nothing here runs automatically:")
    for i, step in enumerate(LIVE_DEMO_CHECKLIST, start=1):
        st.write(f"{i}. {step}")

    st.subheader(DEMO_RECOMMENDATION_LABEL)
    for key, value in DEMO_RECOMMENDATION.items():
        st.write(f"- **{key}:** {value}")
    st.caption(
        "ℹ️ This is a suggested starting point for a demonstration -- it is "
        "not presented as an experimentally proven optimal configuration."
    )

    st.subheader("What to Look For")
    for stage, points in DEMO_RESULT_EXPLANATION.items():
        st.markdown(f"**{stage}:**")
        for point in points:
            st.write(f"- {point}")

    st.info(f"📎 **Key teaching point:** {RECOVERY_PERCENTAGE_TEACHING_POINT}")


def _render_scientific_concepts_section() -> None:
    st.header("Biotechnology Concepts Demonstrated")
    for concept, explanation in SCIENTIFIC_CONCEPTS:
        with st.expander(concept):
            st.write(explanation)


def _render_limitations_section() -> None:
    st.header("Important Limitations")
    st.error(f"**{LIMITATIONS_STATEMENT}**")
    st.write("BioVault does **NOT**:")
    for item in LIMITATIONS_DOES_NOT:
        st.write(f"- {item}")


def _render_architecture_section() -> None:
    st.header("Software Architecture")
    st.code(ARCHITECTURE_DIAGRAM, language="text")
    st.write("Key modules:")
    st.code("\n".join(ARCHITECTURE_KEY_MODULES), language="text")
    st.caption(
        "The application uses modular Python files rather than placing all "
        "logic in one file -- each concept has its own pure, independently "
        "testable module."
    )


def _render_timeline_section() -> None:
    st.header("Project Development Timeline")
    with st.expander("View all phases", expanded=False):
        for phase_number, phase_name in PROJECT_TIMELINE:
            st.write(f"**Phase {phase_number}** -- {phase_name}")


def _render_statistics_section() -> None:
    st.header("Project Statistics")
    stats = get_project_statistics()

    col1, col2, col3 = st.columns(3)
    col1.metric("Phases Completed", stats["phases_completed"])
    col2.metric("Verified Tests Passing", stats["verified_test_count"])
    col3.metric("Application Modules", stats["total_module_files"])

    col4, col5, col6 = st.columns(3)
    col4.metric("UI Pages", stats["ui_page_count"])
    col5.metric("DNA Bases", stats["dna_base_count"])
    col6.metric("Bits per Base", stats["bits_per_base"])

    st.caption(
        "📎 Module and page counts are counted directly from the project's "
        "real files. The verified test count is a documented, manually "
        "updated figure from the last confirmed `pytest -q` run -- see "
        "showcase_content.py."
    )


def _render_slide_outline_section() -> None:
    st.header("Suggested 12-Slide Presentation")
    for slide in SLIDE_OUTLINE:
        with st.expander(slide["title"]):
            for bullet in slide["bullets"]:
                st.write(f"- {bullet}")
            st.caption(f"🗣️ Speaker note: {slide['speaker_note']}")


def _render_future_scope_section() -> None:
    st.header("Future Scope")
    st.caption("Realistic future directions -- none of these are implemented today.")
    for item in FUTURE_SCOPE:
        st.write(f"- {item}")


def _render_conclusion_section() -> None:
    st.header("Conclusion")
    st.write(PROJECT_CONCLUSION)
