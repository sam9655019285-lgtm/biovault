"""
Tests for app/modules/showcase_content.py (Phase 21).

Tests the pure data/content structures only -- never brittle exact-UI-
rendering checks. Verifies presence of required sections, that the
encoding example matches the real encoder, that no physical-DNA-
storage claim or fake experimental result is embedded, and that
project statistics are structurally valid.
"""

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
    LIVE_DEMO_CHECKLIST,
    DEMO_RECOMMENDATION,
    DEMO_RECOMMENDATION_LABEL,
    SCIENTIFIC_CONCEPTS,
    LIMITATIONS_DOES_NOT,
    LIMITATIONS_STATEMENT,
    ARCHITECTURE_DIAGRAM,
    ARCHITECTURE_KEY_MODULES,
    PROJECT_TIMELINE,
    CURRENT_VERIFIED_TEST_COUNT,
    SLIDE_OUTLINE,
    FUTURE_SCOPE,
    PROJECT_CONCLUSION,
    get_project_statistics,
)
from app.modules.dna_encoder import BITS_TO_BASE, encode_file_to_dna


# --- Title / intro -----------------------------------------------------------------

def test_project_title_exists():
    assert APP_TITLE.strip() != ""
    assert APP_SUBTITLE.strip() != ""
    assert INTRO_TEXT.strip() != ""


def test_software_simulation_notice_is_present():
    assert "simulation" in SOFTWARE_SIMULATION_NOTICE.lower()


# --- Problem / objectives -----------------------------------------------------------

def test_problem_statement_exists():
    assert PROBLEM_STATEMENT.strip() != ""


def test_objectives_exist_and_are_non_empty():
    assert len(OBJECTIVES) >= 5
    assert all(isinstance(o, str) and o.strip() != "" for o in OBJECTIVES)


# --- Workflow ------------------------------------------------------------------------

def test_workflow_stages_exist():
    assert len(WORKFLOW_STAGES) >= 5
    assert "DNA Encoding" in WORKFLOW_STAGES or any("Encoding" in s for s in WORKFLOW_STAGES)


# --- Encoding example matches the real encoder ---------------------------------------

def test_encoding_example_matches_real_encoder_mapping():
    chunks = ENCODING_EXAMPLE_BINARY.split()
    expected_bases = [BITS_TO_BASE[chunk] for chunk in chunks]
    assert ENCODING_EXAMPLE_DNA.split() == expected_bases


def test_encoding_example_is_a_real_round_trippable_example():
    # "00 01 10 11" as raw bits, encoded via the real encoder pipeline
    # for a matching byte, must land on the same DNA bases shown.
    binary_str = ENCODING_EXAMPLE_BINARY.replace(" ", "")
    byte_value = int(binary_str, 2)
    result = encode_file_to_dna(bytes([byte_value]))
    assert result["dna_sequence"] == ENCODING_EXAMPLE_DNA.replace(" ", "")


# --- Live demo -------------------------------------------------------------------------

def test_live_demo_checklist_exists():
    assert len(LIVE_DEMO_CHECKLIST) >= 5


def test_demo_recommendation_is_labeled_as_suggestion_not_proven_optimal():
    assert "suggested" in DEMO_RECOMMENDATION_LABEL.lower()
    assert "optimal" in DEMO_RECOMMENDATION_LABEL.lower() or "not proven" in DEMO_RECOMMENDATION_LABEL.lower()
    assert len(DEMO_RECOMMENDATION) > 0


# --- Scientific concepts ---------------------------------------------------------------

def test_scientific_concepts_section_exists():
    assert len(SCIENTIFIC_CONCEPTS) >= 5
    for name, explanation in SCIENTIFIC_CONCEPTS:
        assert name.strip() != ""
        assert explanation.strip() != ""


# --- Limitations section exists and is honest -------------------------------------------

def test_limitations_section_exists():
    assert len(LIMITATIONS_DOES_NOT) >= 5
    assert LIMITATIONS_STATEMENT.strip() != ""


def test_no_claim_of_physical_dna_storage_exists():
    all_text = " ".join(LIMITATIONS_DOES_NOT).lower() + " " + LIMITATIONS_STATEMENT.lower()
    # The limitations section must explicitly deny physical storage/synthesis.
    assert "synthesize" in all_text or "synthesis" in all_text
    assert "sequenc" in all_text  # covers "sequencing"/"sequence"

    combined_project_text = (
        INTRO_TEXT + PROBLEM_STATEMENT + PROJECT_CONCLUSION
    ).lower()
    forbidden_phrases = [
        "physically stored the file in dna",
        "actual dna synthesis was performed",
        "real dna sequencing was performed",
        "laboratory validated",
        "biologically validated",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in combined_project_text


def test_no_fake_experimental_result_is_embedded():
    # The showcase must never claim a specific, invented recovery/
    # experimental outcome as if it were a real measured result.
    combined_text = (INTRO_TEXT + PROBLEM_STATEMENT + PROJECT_CONCLUSION).lower()
    for phrase in ("successfully recovered 100% of all files", "proven to work in laboratory conditions", "experimentally validated results"):
        assert phrase not in combined_text


# --- Architecture -------------------------------------------------------------------------

def test_architecture_section_exists():
    assert ARCHITECTURE_DIAGRAM.strip() != ""
    assert len(ARCHITECTURE_KEY_MODULES) >= 5
    assert "dna_encoder.py" in ARCHITECTURE_KEY_MODULES
    assert "experiment_pipeline.py" in ARCHITECTURE_KEY_MODULES


# --- Timeline --------------------------------------------------------------------------------

def test_timeline_exists_and_is_ordered():
    assert len(PROJECT_TIMELINE) >= 20
    phase_numbers = [phase for phase, _name in PROJECT_TIMELINE]
    assert phase_numbers == sorted(phase_numbers)
    assert phase_numbers[0] == 1


def test_timeline_has_no_empty_names():
    for _phase, name in PROJECT_TIMELINE:
        assert isinstance(name, str) and name.strip() != ""


# --- Slide outline -----------------------------------------------------------------------------

def test_twelve_slide_outline_exists():
    assert len(SLIDE_OUTLINE) == 12
    for slide in SLIDE_OUTLINE:
        assert slide["title"].strip() != ""
        assert 3 <= len(slide["bullets"]) <= 6
        assert slide["speaker_note"].strip() != ""


# --- Future scope --------------------------------------------------------------------------------

def test_future_scope_section_exists():
    assert len(FUTURE_SCOPE) >= 5
    assert all(isinstance(item, str) and item.strip() != "" for item in FUTURE_SCOPE)


def test_future_scope_is_not_claimed_as_already_implemented():
    conclusion_lower = PROJECT_CONCLUSION.lower()
    for item in FUTURE_SCOPE:
        assert item.lower() not in conclusion_lower


# --- Project statistics structure -------------------------------------------------------------------

def test_project_statistics_structure_is_valid():
    stats = get_project_statistics()
    for key in (
        "phases_completed", "verified_test_count", "total_module_files",
        "ui_page_count", "logic_module_count", "dna_base_count", "bits_per_base",
    ):
        assert key in stats
        assert isinstance(stats[key], int)


def test_project_statistics_are_internally_consistent():
    stats = get_project_statistics()
    assert stats["dna_base_count"] == 4
    assert stats["bits_per_base"] == 2
    assert stats["total_module_files"] == stats["ui_page_count"] + stats["logic_module_count"]
    assert stats["phases_completed"] == len(PROJECT_TIMELINE)


def test_verified_test_count_is_a_positive_documented_constant():
    assert isinstance(CURRENT_VERIFIED_TEST_COUNT, int)
    assert CURRENT_VERIFIED_TEST_COUNT > 0


def test_module_counts_are_dynamically_computed_not_hardcoded_zero():
    # A regression guard: if the counting logic ever broke silently
    # (e.g. wrong glob path), these would incorrectly report 0.
    stats = get_project_statistics()
    assert stats["total_module_files"] > 20
    assert stats["ui_page_count"] > 10
