"""
Tests for app/modules/documentation.py.

Plain-Python tests (no Streamlit). Content is checked for the presence
of required sections/terms and accurate, honest descriptions of the
actually-implemented features (no fabricated claims).
Run with:  python -m pytest
"""

from app.modules.documentation import (
    get_sections,
    get_section_by_id,
    get_quick_start,
    get_common_problems,
    get_glossary,
)


REQUIRED_SECTION_IDS = [
    "welcome",
    "getting_started",
    "dna_encoding",
    "dna_decoding",
    "mutation",
    "error_correction",
    "storage_analysis",
    "visualization",
    "export_import",
    "benchmarking",
    "workflow",
    "limitations",
]


# --- All required documentation sections exist --------------------------------

def test_all_required_sections_exist():
    sections = get_sections()
    section_ids = {section["id"] for section in sections}
    for required_id in REQUIRED_SECTION_IDS:
        assert required_id in section_ids


def test_sections_have_title_and_content():
    for section in get_sections():
        assert section["title"].strip() != ""
        assert section["content"].strip() != ""


def test_get_section_by_id_returns_correct_section():
    section = get_section_by_id("dna_encoding")
    assert section is not None
    assert section["id"] == "dna_encoding"


def test_get_section_by_id_returns_none_for_unknown_id():
    assert get_section_by_id("not_a_real_section") is None


# --- Quick Start content exists --------------------------------------------------

def test_quick_start_content_exists_and_mentions_key_steps():
    quick_start = get_quick_start()
    assert quick_start.strip() != ""
    assert "File Upload" in quick_start
    assert "Encode to DNA" in quick_start


# --- Common Problems content exists ------------------------------------------------

def test_common_problems_cover_required_topics():
    problems = get_common_problems()
    problem_texts = " ".join(item["problem"].lower() for item in problems)
    required_topics = [
        "no file uploaded",
        "invalid dna characters",
        "empty dna import",
        "not compatible with decoding",
        "no mutation result",
        "no protected sequence",
        "not available",
        "export buttons",
    ]
    for topic in required_topics:
        assert topic in problem_texts


def test_common_problems_all_have_explanations():
    for item in get_common_problems():
        assert item["problem"].strip() != ""
        assert item["explanation"].strip() != ""


# --- Glossary terms exist ------------------------------------------------------------

def test_glossary_contains_required_terms():
    glossary = get_glossary()
    required_terms = [
        "Nucleotide", "DNA sequence", "Encoding", "Decoding", "Mutation",
        "Substitution", "Insertion", "Deletion", "Checksum", "Redundancy",
        "Storage overhead", "Error correction",
    ]
    for term in required_terms:
        assert term in glossary
        assert glossary[term].strip() != ""


# --- DNA mapping explanation is accurate -----------------------------------------------

def test_encoding_section_describes_actual_2_bit_mapping():
    section = get_section_by_id("dna_encoding")
    content = section["content"]
    for mapping in ["00", "01", "10", "11", "A", "C", "G", "T"]:
        assert mapping in content
    # Must not claim padding is needed -- the real encoder never pads.
    assert "never needs to pad" in content or "never need to pad" in content.lower() or "no bits ever discarded" in content


def test_decoding_section_describes_reverse_mapping_and_honest_errors():
    section = get_section_by_id("dna_decoding")
    content = section["content"]
    assert "A" in content and "00" in content
    assert "multiple of 4" in content
    assert "byte-for-byte" in content


# --- Mutation and error-correction limitations are documented ---------------------------

def test_mutation_section_covers_all_three_mutation_types():
    section = get_section_by_id("mutation")
    content = section["content"].lower()
    assert "substitution" in content
    assert "insertion" in content
    assert "deletion" in content
    assert "mutation rate" in content
    assert "seed" in content


def test_error_correction_section_documents_limitations():
    section = get_section_by_id("error_correction")
    content = section["content"].lower()
    assert "checksum" in content
    assert "cannot be corrected" in content or "cannot correct" in content
    assert "insertion" in content and "deletion" in content
    assert "collision" in content
    # Must not claim biologically accurate DNA-repair technology.
    assert "biologically accurate" in content
    assert "not any kind of advanced" in content or "not" in content


# --- Export/import and benchmarking instructions exist ------------------------------------

def test_export_import_section_covers_required_topics():
    section = get_section_by_id("export_import")
    content = section["content"].lower()
    for topic in ["dna text export", "metadata", "csv", "text report", "import"]:
        assert topic in content


def test_export_import_section_documents_validation_rules():
    section = get_section_by_id("export_import")
    content = section["content"].lower()
    assert "whitespace" in content
    assert "rejected" in content


def test_benchmarking_section_covers_required_topics():
    section = get_section_by_id("benchmarking")
    content = section["content"].lower()
    assert "original" in content
    assert "mutated" in content
    assert "protected" in content
    assert "corrected" in content
    assert "not available" in content


# --- No unsupported feature claims are included --------------------------------------------

def test_no_section_mentions_unsupported_technologies():
    forbidden_terms = [
        "machine learning", "artificial intelligence", "login", "database",
        "fastapi", "django", "postgresql", "react", "pdf report",
        "biological dna repair", "real dna synthesis is performed",
    ]
    all_content = " ".join(section["content"].lower() for section in get_sections())
    for term in forbidden_terms:
        assert term not in all_content


def test_limitations_section_states_simulation_disclaimer():
    section = get_section_by_id("limitations")
    content = section["content"].lower()
    assert "simulation" in content
    assert "not" in content and "laboratory" in content


def test_welcome_section_states_educational_purpose():
    section = get_section_by_id("welcome")
    content = section["content"].lower()
    assert "educational" in content
    assert "not" in content


# --- Documentation content is returned correctly / deterministic ----------------------------

def test_get_sections_is_deterministic():
    assert get_sections() == get_sections()


def test_get_glossary_is_deterministic():
    assert get_glossary() == get_glossary()


def test_get_common_problems_is_deterministic():
    assert get_common_problems() == get_common_problems()


# --- Workflow section matches the actual application flow -----------------------------------

def test_workflow_section_lists_real_stages_in_order():
    section = get_section_by_id("workflow")
    content = section["content"]
    stages = ["Upload file", "Encode DNA", "Simulate mutations", "Apply error correction",
              "Analyze storage", "View visualization", "Run benchmarking", "Export results",
              "Import and decode"]
    positions = [content.find(stage) for stage in stages]
    assert all(pos != -1 for pos in positions)
    assert positions == sorted(positions)
