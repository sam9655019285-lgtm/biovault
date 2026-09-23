"""
Tests for app/modules/viva_questions.py (Phase 21).

Covers question-bank completeness, category validity, no empty
questions/answers, random selection, major-topic coverage, and no
duplicate question IDs.
"""

import pytest

from app.modules.viva_questions import (
    VivaQuestionsError,
    CATEGORIES,
    QUESTIONS,
    get_categories,
    get_all_questions,
    get_questions_by_category,
    get_question_by_id,
    get_question_count,
)


def test_at_least_25_questions_exist():
    assert get_question_count() >= 25


def test_every_question_has_a_non_empty_answer():
    for question in QUESTIONS:
        assert isinstance(question["answer"], str)
        assert question["answer"].strip() != ""


def test_no_empty_questions():
    for question in QUESTIONS:
        assert isinstance(question["question"], str)
        assert question["question"].strip() != ""


def test_categories_are_valid():
    for question in QUESTIONS:
        assert question["category"] in CATEGORIES


def test_get_categories_matches_actual_question_categories():
    used_categories = {q["category"] for q in QUESTIONS}
    assert used_categories == set(get_categories())


def test_random_selection_returns_a_valid_question():
    import random

    question = random.choice(get_all_questions())
    assert question in QUESTIONS
    assert question["question"].strip() != ""
    assert question["answer"].strip() != ""


def test_no_duplicate_question_ids():
    ids = [q["id"] for q in QUESTIONS]
    assert len(ids) == len(set(ids))


def test_get_question_by_id_returns_correct_question():
    first_id = QUESTIONS[0]["id"]
    result = get_question_by_id(first_id)
    assert result["id"] == first_id


def test_get_question_by_id_raises_for_unknown_id():
    with pytest.raises(VivaQuestionsError):
        get_question_by_id("not-a-real-id")


def test_get_questions_by_category_returns_only_matching_questions():
    for category in get_categories():
        questions = get_questions_by_category(category)
        assert len(questions) > 0
        assert all(q["category"] == category for q in questions)


def test_get_all_questions_returns_a_copy_not_the_original_list():
    questions = get_all_questions()
    questions.append({"id": "fake", "category": "x", "question": "x", "answer": "x"})
    assert len(get_all_questions()) == len(QUESTIONS)


# --- Major topic coverage (from the phase's required categories) ------------------

@pytest.mark.parametrize(
    "expected_category",
    [
        "Basic Biotechnology",
        "Computer / Encoding",
        "Error Handling",
        "Integrity",
        "Storage / Capacity",
        "Project",
    ],
)
def test_all_required_major_categories_are_represented(expected_category):
    assert expected_category in get_categories()
    assert len(get_questions_by_category(expected_category)) > 0


def test_key_concepts_are_covered_by_at_least_one_question():
    all_text = " ".join(f"{q['question']} {q['answer']}" for q in QUESTIONS).lower()
    for keyword in ("sha-256", "substitution", "insertion", "deletion", "redundancy", "bits", "mutation"):
        assert keyword in all_text
