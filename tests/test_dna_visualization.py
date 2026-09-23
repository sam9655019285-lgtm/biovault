"""
Tests for app/modules/dna_visualization.py.

Plain-Python tests (no Streamlit). All functions here are pure
data-preparation logic, so results are fully deterministic.
Run with:  python -m pytest
"""

import pytest

from app.modules.dna_visualization import (
    DNAVisualizationError,
    count_dna_bases,
    calculate_base_percentages,
    prepare_base_composition_data,
    prepare_length_comparison_data,
    prepare_mutation_statistics_data,
    prepare_error_correction_data,
    prepare_storage_overhead_data,
)


# 1. Valid DNA base counting -------------------------------------------------

def test_count_dna_bases_valid_sequence():
    counts = count_dna_bases("AATTGGCC")
    assert counts == {"A": 2, "T": 2, "G": 2, "C": 2, "total": 8}


def test_count_dna_bases_normalizes_lowercase():
    counts = count_dna_bases("aattggcc")
    assert counts["A"] == 2 and counts["total"] == 8


# 2. Empty DNA handling --------------------------------------------------------

def test_count_dna_bases_rejects_empty_sequence():
    with pytest.raises(DNAVisualizationError):
        count_dna_bases("")


# 3. Invalid DNA rejection --------------------------------------------------------

def test_count_dna_bases_rejects_invalid_characters():
    with pytest.raises(DNAVisualizationError):
        count_dna_bases("ACGTX")


def test_count_dna_bases_rejects_non_string():
    with pytest.raises(DNAVisualizationError):
        count_dna_bases(1234)  # type: ignore[arg-type]


# 4. Base percentages -----------------------------------------------------------

def test_calculate_base_percentages_even_split():
    percentages = calculate_base_percentages("AATTGGCC")
    assert percentages == {"A": 25.0, "T": 25.0, "G": 25.0, "C": 25.0}


# 5. Percentages summing to approximately 100% -----------------------------------

@pytest.mark.parametrize("sequence", ["A", "AC", "AACCGT", "ACGTACGTACG", "A" * 37])
def test_percentages_sum_to_approximately_100(sequence):
    percentages = calculate_base_percentages(sequence)
    total = sum(percentages.values())
    assert 99.9 <= total <= 100.1


# 6. Base-composition data preparation --------------------------------------------

def test_prepare_base_composition_data_structure():
    df = prepare_base_composition_data("AATTGGCC")
    assert list(df.columns) == ["Base", "Count", "Percentage"]
    assert set(df["Base"]) == {"A", "T", "G", "C"}
    assert df["Count"].sum() == 8


def test_prepare_base_composition_data_rejects_invalid_sequence():
    with pytest.raises(DNAVisualizationError):
        prepare_base_composition_data("")


# 7. DNA length comparison data ----------------------------------------------------

def test_prepare_length_comparison_data_original_only():
    df = prepare_length_comparison_data(100)
    assert list(df["Stage"]) == ["Original DNA"]
    assert list(df["Length (bases)"]) == [100]


def test_prepare_length_comparison_data_with_mutation_and_protection():
    df = prepare_length_comparison_data(100, mutated_length=105, protected_length=150)
    assert list(df["Stage"]) == ["Original DNA", "Mutated DNA", "Protected DNA"]
    assert list(df["Length (bases)"]) == [100, 105, 150]


def test_prepare_length_comparison_data_omits_missing_values_not_zero():
    df = prepare_length_comparison_data(100, mutated_length=None, protected_length=50)
    # Mutated DNA must be entirely absent, not shown as 0.
    assert "Mutated DNA" not in list(df["Stage"])
    assert "Protected DNA" in list(df["Stage"])


def test_prepare_length_comparison_data_rejects_negative_length():
    with pytest.raises(DNAVisualizationError):
        prepare_length_comparison_data(-5)


# 8. Missing mutation data handling ------------------------------------------------

def test_prepare_mutation_statistics_data_returns_none_for_missing_fields():
    assert prepare_mutation_statistics_data({"original_length": 10}) is None


def test_prepare_mutation_statistics_data_returns_none_for_non_dict():
    assert prepare_mutation_statistics_data(None) is None


# 9. Mutation statistics preparation ------------------------------------------------

def test_prepare_mutation_statistics_data_valid_stats():
    stats = {
        "original_length": 100,
        "mutated_length": 108,
        "mutation_type": "insertion",
        "mutation_rate": 10,
        "substitutions": 0,
        "insertions": 8,
        "deletions": 0,
        "total_edits": 8,
    }
    prepared = prepare_mutation_statistics_data(stats)
    assert prepared is not None
    assert prepared["summary"]["length_difference"] == 8
    assert prepared["summary"]["length_changed"] is True
    assert list(prepared["edit_breakdown"]["Count"]) == [0, 8, 0]


def test_prepare_mutation_statistics_data_no_length_change_for_substitution():
    stats = {
        "original_length": 50, "mutated_length": 50, "mutation_type": "substitution",
        "mutation_rate": 20, "substitutions": 5, "insertions": 0, "deletions": 0, "total_edits": 5,
    }
    prepared = prepare_mutation_statistics_data(stats)
    assert prepared["summary"]["length_changed"] is False


# 10. Missing error-correction data handling ------------------------------------------

def test_prepare_error_correction_data_returns_none_for_missing_fields():
    assert prepare_error_correction_data({"blocks_checked": 5}) is None


def test_prepare_error_correction_data_returns_none_for_non_dict():
    assert prepare_error_correction_data(None) is None


# 11. Error-correction statistics preparation -------------------------------------------

def test_prepare_error_correction_data_valid_result():
    correction_result = {
        "blocks_checked": 10,
        "errors_detected": 3,
        "errors_corrected": 2,
        "uncorrectable_errors": 1,
        "correction_success": False,
    }
    prepared = prepare_error_correction_data(correction_result)
    assert prepared is not None
    assert prepared["summary"]["errors_corrected"] == 2
    assert list(prepared["breakdown"]["Count"]) == [2, 1]


def test_prepare_error_correction_data_zero_errors():
    correction_result = {
        "blocks_checked": 5, "errors_detected": 0, "errors_corrected": 0,
        "uncorrectable_errors": 0, "correction_success": True,
    }
    prepared = prepare_error_correction_data(correction_result)
    assert prepared["summary"]["correction_success"] is True
    assert list(prepared["breakdown"]["Count"]) == [0, 0]


# 12. Storage-overhead data preparation -----------------------------------------------

def test_prepare_storage_overhead_data_without_redundancy():
    report = {
        "file_size_bytes": 100,
        "capacity_info": {"dna_length": 400, "capacity_bits": 800, "capacity_bytes": 100.0},
        "raw_efficiency_percent": 100.0,
        "redundancy_info": None,
        "mutation_info": None,
    }
    prepared = prepare_storage_overhead_data(report)
    assert prepared["summary"]["redundancy_bases"] is None
    assert list(prepared["breakdown"]["Metric"]) == ["Encoded DNA"]


def test_prepare_storage_overhead_data_with_redundancy():
    report = {
        "file_size_bytes": 100,
        "capacity_info": {"dna_length": 400, "capacity_bits": 800, "capacity_bytes": 100.0},
        "raw_efficiency_percent": 100.0,
        "redundancy_info": {
            "dna_length": 400, "block_size": 4, "redundancy_size": 2,
            "num_blocks": 100, "redundancy_bases": 200, "protected_length": 600,
            "overhead_percent": 50.0,
        },
        "mutation_info": None,
    }
    prepared = prepare_storage_overhead_data(report)
    assert prepared["summary"]["redundancy_bases"] == 200
    assert prepared["summary"]["overhead_percent"] == 50.0
    assert list(prepared["breakdown"]["Metric"]) == ["Encoded DNA", "Redundancy Overhead"]


# 13. Missing storage-analysis data handling ----------------------------------------------

def test_prepare_storage_overhead_data_returns_none_for_missing_fields():
    assert prepare_storage_overhead_data({"file_size_bytes": 10}) is None


def test_prepare_storage_overhead_data_returns_none_for_non_dict():
    assert prepare_storage_overhead_data(None) is None


# 14. Required output fields --------------------------------------------------------------

def test_prepare_mutation_statistics_data_required_summary_fields():
    stats = {
        "original_length": 10, "mutated_length": 10, "mutation_type": "substitution",
        "mutation_rate": 5, "substitutions": 1, "insertions": 0, "deletions": 0, "total_edits": 1,
    }
    prepared = prepare_mutation_statistics_data(stats)
    required = {
        "mutation_type", "mutation_rate", "original_length", "mutated_length",
        "length_difference", "length_changed", "total_edits",
    }
    assert required <= set(prepared["summary"].keys())


# 15. Deterministic results -----------------------------------------------------------------

def test_prepare_base_composition_data_is_deterministic():
    df_a = prepare_base_composition_data("ACGTACGTACGT")
    df_b = prepare_base_composition_data("ACGTACGTACGT")
    assert df_a.equals(df_b)


def test_count_dna_bases_is_deterministic():
    assert count_dna_bases("ACGTACGT") == count_dna_bases("ACGTACGT")
