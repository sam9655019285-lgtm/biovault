"""
Tests for app/modules/project_summary.py.

Plain-Python tests (no Streamlit). All calculations here are pure
extraction/arithmetic over already-computed result dicts, so results
are fully deterministic.
Run with:  python -m pytest
"""

from app.modules.project_summary import (
    get_original_file_summary,
    get_encoding_summary,
    get_mutation_summary,
    get_error_correction_summary,
    get_storage_summary,
    get_benchmarking_summary,
    build_dashboard_summary,
    get_experiment_status,
    get_project_progress,
    get_presentation_content,
    PROJECT_STAGES,
)


# --- Dashboard summary generation ------------------------------------------------

def test_build_dashboard_summary_structure():
    summary = build_dashboard_summary()
    required_keys = {
        "app_name", "file_summary", "encoding_summary", "mutation_summary",
        "correction_summary", "storage_summary", "benchmarking_summary",
    }
    assert required_keys <= set(summary.keys())
    assert summary["app_name"] == "BioVault"


# --- Missing-data handling ----------------------------------------------------------

def test_build_dashboard_summary_all_none_when_no_data():
    summary = build_dashboard_summary()
    assert summary["file_summary"] is None
    assert summary["encoding_summary"] is None
    assert summary["mutation_summary"] is None
    assert summary["correction_summary"] is None
    assert summary["storage_summary"] is None
    assert summary["benchmarking_summary"] is None


# --- Original file information -------------------------------------------------------

def test_get_original_file_summary_valid():
    file_info = {"filename": "test.txt", "size_bytes": 100, "category": "Text"}
    result = get_original_file_summary(file_info)
    assert result == {"filename": "test.txt", "size_bytes": 100, "category": "Text"}


def test_get_original_file_summary_none_when_missing():
    assert get_original_file_summary(None) is None
    assert get_original_file_summary({}) is None


# --- Encoding status ------------------------------------------------------------------

def test_get_encoding_summary_valid():
    encoding_result = {"dna_length": 400, "binary_length_bits": 800}
    result = get_encoding_summary(encoding_result)
    assert result["dna_length"] == 400
    assert result["binary_length_bits"] == 800


def test_get_encoding_summary_none_when_missing():
    assert get_encoding_summary(None) is None


# --- Mutation status ------------------------------------------------------------------

def test_get_mutation_summary_valid():
    mutation_result = {
        "mutation_type": "substitution", "mutation_rate": 10,
        "stats": {"mutated_length": 400, "total_edits": 5},
    }
    result = get_mutation_summary(mutation_result)
    assert result["mutation_type"] == "substitution"
    assert result["mutated_length"] == 400
    assert result["total_edits"] == 5


def test_get_mutation_summary_none_when_missing():
    assert get_mutation_summary(None) is None
    assert get_mutation_summary({}) is None


# --- Error-correction status -----------------------------------------------------------

def test_get_error_correction_summary_valid():
    correction_result = {
        "protected_sequence": "A" * 150,
        "correction": {
            "corrected_sequence": "A" * 100,
            "errors_detected": 2,
            "errors_corrected": 2,
            "uncorrectable_errors": 0,
            "correction_success": True,
        },
    }
    result = get_error_correction_summary(correction_result)
    assert result["protected_length"] == 150
    assert result["corrected_length"] == 100
    assert result["errors_detected"] == 2
    assert result["errors_corrected"] == 2
    assert result["recovery_confirmed"] is True


def test_get_error_correction_summary_none_when_missing():
    assert get_error_correction_summary(None) is None


# --- Storage-analysis status --------------------------------------------------------------

def test_get_storage_summary_valid_with_redundancy():
    analysis_result = {
        "report": {
            "raw_efficiency_percent": 100.0,
            "redundancy_info": {"overhead_percent": 50.0},
        }
    }
    result = get_storage_summary(analysis_result)
    assert result["raw_efficiency_percent"] == 100.0
    assert result["overhead_percent"] == 50.0


def test_get_storage_summary_overhead_none_without_redundancy_info():
    analysis_result = {"report": {"raw_efficiency_percent": 100.0, "redundancy_info": None}}
    result = get_storage_summary(analysis_result)
    assert result["overhead_percent"] is None


def test_get_storage_summary_none_when_missing():
    assert get_storage_summary(None) is None


# --- Benchmarking status ---------------------------------------------------------------------

def test_get_benchmarking_summary_valid():
    benchmarking_result = {
        "benchmark": {
            "mutation_stats": {"mutated_length": 100},
            "correction_stats": None,
        }
    }
    result = get_benchmarking_summary(benchmarking_result)
    assert result["available"] is True
    assert result["has_mutation_data"] is True
    assert result["has_correction_data"] is False


def test_get_benchmarking_summary_none_when_missing():
    assert get_benchmarking_summary(None) is None


# --- Recovery-status honesty --------------------------------------------------------------------

def test_recovery_confirmed_false_unless_explicit_success():
    correction_result = {
        "protected_sequence": "A" * 150,
        "correction": {
            "corrected_sequence": "A" * 90,
            "errors_detected": 3,
            "errors_corrected": 2,
            "uncorrectable_errors": 1,
            "correction_success": False,
        },
    }
    result = get_error_correction_summary(correction_result)
    assert result["recovery_confirmed"] is False


def test_recovery_confirmed_false_when_success_field_missing():
    correction_result = {"protected_sequence": "A" * 10, "correction": {}}
    result = get_error_correction_summary(correction_result)
    assert result["recovery_confirmed"] is False


# --- Project workflow summary -----------------------------------------------------------------

def test_get_project_progress_matches_actual_stage_list():
    progress = get_project_progress()
    assert progress == PROJECT_STAGES
    assert "File Upload" in progress
    assert "User Guide" in progress
    assert "DNA Storage Capacity & Information Density" in progress
    assert "DNA Storage Experiment (end-to-end)" in progress
    assert "Project Showcase & Viva Preparation" in progress
    assert "Environment & Setup Check" in progress
    assert len(progress) == 14


def test_get_project_progress_returns_a_copy_not_the_original_list():
    progress = get_project_progress()
    progress.append("Fake Stage")
    assert "Fake Stage" not in get_project_progress()


# --- Presentation content ------------------------------------------------------------------------

def test_presentation_content_has_required_fields():
    content = get_presentation_content()
    required_fields = {
        "title", "problem_statement", "objectives", "workflow", "technologies",
        "limitations", "future_improvements", "educational_significance",
        "simulation_disclaimer",
    }
    assert required_fields <= set(content.keys())


def test_presentation_content_objectives_cover_required_topics():
    content = get_presentation_content()
    objectives_text = " ".join(content["objectives"]).lower()
    for topic in ["convert digital file data", "recover the original file", "substitutions, insertions, and deletions",
                  "error-correction", "storage efficiency", "visualize and compare", "export and import"]:
        assert topic in objectives_text


def test_presentation_content_technologies_are_accurate():
    content = get_presentation_content()
    assert "Python" in content["technologies"]
    assert "Streamlit" in content["technologies"]
    # Must not claim unsupported technologies.
    forbidden = ["React", "FastAPI", "Django", "PostgreSQL", "TensorFlow", "PyTorch"]
    for tech in forbidden:
        assert tech not in content["technologies"]


def test_presentation_content_states_simulation_disclaimer():
    content = get_presentation_content()
    disclaimer = content["simulation_disclaimer"].lower()
    assert "simulation" in disclaimer
    assert "not" in disclaimer and "real dna synthesis" in disclaimer


# --- Limitation content --------------------------------------------------------------------------

def test_limitations_mention_required_topics():
    content = get_presentation_content()
    limitations_text = " ".join(content["limitations"]).lower()
    for topic in ["simplified", "checksum", "collision", "insertion", "deletion",
                  "no real dna synthesis", "no laboratory"]:
        assert topic in limitations_text


def test_future_improvements_are_clearly_separate_from_limitations():
    content = get_presentation_content()
    # Future ideas must not overlap with the stated limitations list --
    # they are explicitly unimplemented, not current shortcomings.
    assert set(content["future_improvements"]).isdisjoint(set(content["limitations"]))


# --- No fabricated values -----------------------------------------------------------------------

def test_error_correction_summary_length_none_when_no_corrected_sequence():
    correction_result = {
        "protected_sequence": "A" * 50,
        "correction": {
            "corrected_sequence": None,
            "errors_detected": None,
            "errors_corrected": 0,
            "uncorrectable_errors": None,
            "correction_success": False,
        },
    }
    result = get_error_correction_summary(correction_result)
    assert result["corrected_length"] is None  # never fabricated as 0
    assert result["errors_detected"] is None


# --- Experiment status (session-state/source matching behavior) ---------------------------------

def test_experiment_status_no_file():
    assert get_experiment_status() == "No file uploaded"


def test_experiment_status_file_but_no_encoding():
    status = get_experiment_status(file_info={"filename": "a.txt"})
    assert status == "File uploaded but not encoded"


def test_experiment_status_encoded_only():
    status = get_experiment_status(file_info={"filename": "a.txt"}, encoding_result={"dna_length": 10})
    assert status == "DNA encoded"


def test_experiment_status_most_advanced_stage_wins():
    status = get_experiment_status(
        file_info={"filename": "a.txt"},
        encoding_result={"dna_length": 10},
        mutation_result={"mutation_type": "substitution"},
        correction_result={"correction": {}},
        benchmarking_result={"benchmark": {}},
    )
    assert status == "Benchmark available"


def test_experiment_status_correction_before_mutation_priority():
    status = get_experiment_status(
        file_info={"filename": "a.txt"},
        encoding_result={"dna_length": 10},
        mutation_result={"mutation_type": "substitution"},
        correction_result={"correction": {}},
    )
    assert status == "Error-correction result available"


# --- Existing project compatibility --------------------------------------------------------------

def test_dashboard_summary_uses_real_module_data_end_to_end():
    from app.modules.dna_encoder import encode_file_to_dna
    from app.modules.dna_mutator import mutate_dna
    from app.modules.dna_error_correction import add_redundancy, correct_substitution_errors

    original = b"Dashboard integration test"
    enc = encode_file_to_dna(original)
    file_info = {"filename": "dash.bin", "size_bytes": len(original), "category": "Unknown"}
    encoding_result = {"dna_length": enc["dna_length"], "binary_length_bits": enc["binary_length_bits"]}

    mutation_stats = mutate_dna(enc["dna_sequence"], "substitution", 0, seed=1)
    mutation_result = {
        "mutation_type": mutation_stats["mutation_type"],
        "mutation_rate": mutation_stats["mutation_rate"],
        "stats": mutation_stats,
    }

    protection = add_redundancy(enc["dna_sequence"], block_size=4, redundancy_size=2)
    correction = correct_substitution_errors(
        protection["protected_sequence"], block_size=4, redundancy_size=2, original_length=protection["original_length"]
    )
    correction_result = {"protected_sequence": protection["protected_sequence"], "correction": correction}

    summary = build_dashboard_summary(file_info, encoding_result, mutation_result, correction_result)
    assert summary["encoding_summary"]["dna_length"] == enc["dna_length"]
    assert summary["mutation_summary"]["mutated_length"] == mutation_stats["mutated_length"]
    assert summary["correction_summary"]["recovery_confirmed"] is True

    status = get_experiment_status(file_info, encoding_result, mutation_result, correction_result)
    assert status == "Error-correction result available"
