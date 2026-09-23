"""
UI module: Viva Preparation page.

Presents a local, offline viva/oral-exam question bank (viva_questions.py)
with category and question selection, a "Show Answer" toggle, a random-
question button, and a simple progress indicator. This file only handles
presentation; the question/answer content lives in viva_questions.py.
"""

import random

import streamlit as st

from app.modules.viva_questions import (
    get_categories,
    get_all_questions,
    get_questions_by_category,
    get_question_by_id,
    get_question_count,
)

VIEWED_QUESTIONS_SESSION_KEY = "viva_viewed_question_ids"
CURRENT_QUESTION_SESSION_KEY = "viva_current_question_id"


def render_viva() -> None:
    """Render the Viva Preparation page."""

    st.header("🎤 Viva Preparation")
    st.write(
        "A local, offline question-and-answer bank for viva voce, project "
        "review, or classroom Q&A preparation -- organized by category, "
        "with concise, factually conservative answers."
    )

    viewed = st.session_state.setdefault(VIEWED_QUESTIONS_SESSION_KEY, set())
    total = get_question_count()
    st.progress(len(viewed) / total if total else 0.0)
    st.caption(f"Viewed {len(viewed)} of {total} questions this session.")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🎲 Random Question"):
            question = random.choice(get_all_questions())
            st.session_state[CURRENT_QUESTION_SESSION_KEY] = question["id"]

    with col1:
        categories = ("All Categories",) + get_categories()
        selected_category = st.selectbox("Category", categories)

    questions = get_all_questions() if selected_category == "All Categories" else get_questions_by_category(selected_category)
    if not questions:
        st.info("No questions in this category.")
        return

    question_labels = [f"{q['id']} -- {q['question']}" for q in questions]
    current_id = st.session_state.get(CURRENT_QUESTION_SESSION_KEY)
    default_index = 0
    if current_id:
        matching_indices = [i for i, q in enumerate(questions) if q["id"] == current_id]
        if matching_indices:
            default_index = matching_indices[0]

    selected_label = st.selectbox("Question", question_labels, index=default_index)
    selected_question = questions[question_labels.index(selected_label)]
    st.session_state[CURRENT_QUESTION_SESSION_KEY] = selected_question["id"]

    st.divider()
    st.markdown(f"**Category:** {selected_question['category']}")
    st.markdown(f"### {selected_question['question']}")

    show_key = f"viva_show_answer_{selected_question['id']}"
    if st.button("👁️ Show Answer", key=f"btn_{selected_question['id']}"):
        st.session_state[show_key] = True
        viewed.add(selected_question["id"])
        st.session_state[VIEWED_QUESTIONS_SESSION_KEY] = viewed

    if st.session_state.get(show_key):
        st.success(selected_question["answer"])
    else:
        st.info("Click **Show Answer** when you're ready to check your response.")

    with st.expander("📋 All categories at a glance"):
        for category in get_categories():
            count = len(get_questions_by_category(category))
            st.write(f"- **{category}** -- {count} question(s)")
