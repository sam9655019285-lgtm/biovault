"""
Tests for app/modules/benchmarking.py.

Plain-Python tests (no Streamlit). All calculations here are pure
arithmetic over already-computed result dicts, so results are fully
deterministic.
Run with:  python -m pytest
"""

import pytest

from app.modules.benchmarking import (
    BenchmarkingError,
    NOT_AVAILABLE,
    calculate_original_statistics,
    calculate_mutation_comparison,
    calculate_error_correction_comparison,
    calculate_storage_overhead_comparison,
    build_comparison_table,
    prepare_benchmark_chart_data,
    generate_benchmark_summary,
    run_benchmark,
)


# --- Empty or missing input data --------------------------------------------

def test_original_statistics_none_when_no_file_info():
    assert calculate_original_statistics(None, {"dna_length": 100, "binary_length_bits": 200}) is None


def test_original_statistics_none_when_no_encoding_result():
    assert calculate_original_statistics({"filename": "a.txt", "size_bytes": 10}, None) is None


def test_mutation_comparison_none_when_no_result():
    assert calculate_mutation_comparison(None) is None


def test_error_correction_comparison_none_when_no_result():
    assert calculate_error_correction_comparison(None) is None


def test_storage_overhead_none_when_lengths_missing():
    assert calculate_storage_overhead_comparison(None, 100) is None
    assert calculate_storage_overhead_comparison(100, None) is None


# --- Original sequence statistics ---------------------------------------------

def test_original_statistics_valid():
    file_info = {"filename": "a.txt", "size_bytes": 25}
    encoding_result = {"dna_length": 100, "binary_length_bits": 200}
    result = calculate_original_statistics(file_info, encoding_result)
    assert result["dna_length"] == 100
    assert result["file_size_bytes"] == 25
    assert result["bits_represented"] == 200
    assert result["theoretical_capacity_bits"] == 200
    assert result["bits_per_nucleotide"] == 2


# --- Mutation statistics -----------------------------------------------------------

def test_mutation_comparison_valid():
    mutation_result = {
        "mutation_rate": 15,
        "stats": {
            "original_length": 100, "mutated_length": 105,
            "substitutions": 2, "insertions": 3, "deletions": 0,
        },
    }
    result = calculate_mutation_comparison(mutation_result)
    assert result["mutated_length"] == 105
    assert result["substitutions"] == 2
    assert result["insertions"] == 3
    assert result["deletions"] == 0
    assert result["mutation_rate"] == 15


def test_mutation_comparison_missing_stats_fields_returns_none():
    assert calculate_mutation_comparison({"stats": {"original_length": 10}}) is None


# --- Error-correction statistics ----------------------------------------------------

def test_error_correction_comparison_valid():
    correction_result = {
        "protected_sequence": "A" * 150,
        "correction": {
            "corrected_sequence": "A" * 100,
            "errors_detected": 3,
            "errors_corrected": 2,
            "uncorrectable_errors": 1,
            "correction_success": False,
        },
    }
    result = calculate_error_correction_comparison(correction_result)
    assert result["protected_length"] == 150
    assert result["corrected_length"] == 100
    assert result["errors_detected"] == 3
    assert result["errors_corrected"] == 2
    assert result["uncorrectable_errors"] == 1
    assert result["correction_success"] is False


def test_error_correction_comparison_handles_missing_corrected_sequence():
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
    result = calculate_error_correction_comparison(correction_result)
    assert result["protected_length"] == 50
    assert result["corrected_length"] is None
    assert result["errors_detected"] is None


# --- Storage overhead calculations -------------------------------------------------------

def test_storage_overhead_calculation():
    result = calculate_storage_overhead_comparison(100, 150)
    assert result["additional_nucleotides"] == 50
    assert result["overhead_percent"] == 50.0
    assert result["efficiency_percent"] == round(100 / 150 * 100, 2)


def test_storage_overhead_zero_original_length_does_not_crash():
    result = calculate_storage_overhead_comparison(0, 0)
    assert result["overhead_percent"] == 0.0
    assert result["efficiency_percent"] == 0.0


def test_storage_overhead_rejects_negative_length():
    with pytest.raises(BenchmarkingError):
        calculate_storage_overhead_comparison(-1, 100)


# --- Missing values / no fabricated zero values ---------------------------------------------

def test_comparison_table_shows_not_available_for_missing_sections():
    table = build_comparison_table(None, None, None)
    length_row = table[table["Metric"] == "Sequence Length (bases)"].iloc[0]
    assert length_row["Original"] == NOT_AVAILABLE
    assert length_row["Mutated"] == NOT_AVAILABLE
    assert length_row["Protected"] == NOT_AVAILABLE
    assert length_row["Corrected"] == NOT_AVAILABLE


def test_comparison_table_never_shows_fabricated_zero():
    # A correction_stats dict where corrected_length genuinely wasn't
    # computed (None) must show "Not available", never "0".
    correction_stats = {
        "protected_length": 120, "corrected_length": None,
        "errors_detected": None, "errors_corrected": 0,
        "uncorrectable_errors": None, "correction_success": False,
    }
    table = build_comparison_table(None, None, correction_stats)
    length_row = table[table["Metric"] == "Sequence Length (bases)"].iloc[0]
    assert length_row["Corrected"] == NOT_AVAILABLE
    errors_row = table[table["Metric"] == "Errors Detected"].iloc[0]
    assert errors_row["Protected"] == NOT_AVAILABLE  # None, not fabricated 0


# --- Zero-length and invalid-length cases --------------------------------------------------

def test_original_statistics_zero_length_is_valid_not_missing():
    file_info = {"filename": "empty.txt", "size_bytes": 0}
    encoding_result = {"dna_length": 0, "binary_length_bits": 0}
    result = calculate_original_statistics(file_info, encoding_result)
    assert result is not None
    assert result["dna_length"] == 0
    assert result["theoretical_capacity_bits"] == 0


# --- Benchmark comparison table data --------------------------------------------------------

def test_build_comparison_table_columns():
    table = build_comparison_table(None, None, None)
    assert list(table.columns) == ["Metric", "Original", "Mutated", "Protected", "Corrected"]


def test_build_comparison_table_with_full_data():
    original_stats = {"dna_length": 100, "file_size_bytes": 25, "bits_represented": 200,
                       "theoretical_capacity_bits": 200, "bits_per_nucleotide": 2}
    mutation_stats = {"original_length": 100, "mutated_length": 105, "substitutions": 2,
                       "insertions": 3, "deletions": 0, "mutation_rate": 10}
    correction_stats = {"protected_length": 150, "corrected_length": 100, "errors_detected": 2,
                         "errors_corrected": 2, "uncorrectable_errors": 0, "correction_success": True}
    table = build_comparison_table(original_stats, mutation_stats, correction_stats)
    length_row = table[table["Metric"] == "Sequence Length (bases)"].iloc[0]
    assert length_row["Original"] == 100
    assert length_row["Mutated"] == 105
    assert length_row["Protected"] == 150
    assert length_row["Corrected"] == 100


# --- Successful benchmark generation ---------------------------------------------------------

def test_run_benchmark_with_full_pipeline_data_using_real_modules():
    from app.modules.dna_encoder import encode_file_to_dna
    from app.modules.dna_mutator import mutate_dna
    from app.modules.dna_error_correction import add_redundancy, correct_substitution_errors

    original = b"Benchmark test data"
    enc = encode_file_to_dna(original)
    encoding_result = {"dna_length": enc["dna_length"], "binary_length_bits": enc["binary_length_bits"], "dna_sequence": enc["dna_sequence"]}
    file_info = {"filename": "bench.bin", "size_bytes": len(original)}

    mutation_stats = mutate_dna(enc["dna_sequence"], "substitution", 0, seed=1)  # zero rate -> no errors
    mutation_result = {"mutation_rate": mutation_stats["mutation_rate"], "stats": mutation_stats}

    protection = add_redundancy(enc["dna_sequence"], block_size=4, redundancy_size=2)
    correction = correct_substitution_errors(
        protection["protected_sequence"], block_size=4, redundancy_size=2, original_length=protection["original_length"]
    )
    correction_result = {"protected_sequence": protection["protected_sequence"], "correction": correction}

    benchmark = run_benchmark(file_info, encoding_result, mutation_result, correction_result)

    assert benchmark["original_stats"]["dna_length"] == enc["dna_length"]
    assert benchmark["mutation_stats"]["mutated_length"] == mutation_stats["mutated_length"]
    assert benchmark["correction_stats"]["protected_length"] == len(protection["protected_sequence"])
    assert benchmark["storage_stats"] is not None
    # Zero-rate mutation + no injected errors -> correction should report full success.
    assert benchmark["summary"]["recovery_confirmed"] is True
    assert benchmark["summary"]["correction_restored_length"] is True


def test_run_benchmark_with_no_data_still_returns_structure():
    benchmark = run_benchmark()
    assert benchmark["original_stats"] is None
    assert benchmark["mutation_stats"] is None
    assert benchmark["correction_stats"] is None
    assert benchmark["storage_stats"] is None
    assert benchmark["chart_data"] is None
    assert benchmark["summary"]["recovery_confirmed"] is False


# --- Session-state/source matching behavior (chart data availability) ------------------------

def test_prepare_benchmark_chart_data_none_without_original_stats():
    assert prepare_benchmark_chart_data(None, None, None) is None


def test_prepare_benchmark_chart_data_includes_corrected_row_when_available():
    original_stats = {"dna_length": 100, "file_size_bytes": 10, "bits_represented": 200,
                       "theoretical_capacity_bits": 200, "bits_per_nucleotide": 2}
    correction_stats = {"protected_length": 150, "corrected_length": 100, "errors_detected": 0,
                         "errors_corrected": 0, "uncorrectable_errors": 0, "correction_success": True}
    chart_df = prepare_benchmark_chart_data(original_stats, None, correction_stats)
    assert "Corrected DNA" in list(chart_df["Stage"])


# --- No fabricated zero values in summary -----------------------------------------------------

def test_summary_does_not_claim_recovery_without_success_flag():
    correction_stats = {"protected_length": 150, "corrected_length": 100, "errors_detected": 3,
                         "errors_corrected": 2, "uncorrectable_errors": 1, "correction_success": False}
    original_stats = {"dna_length": 100, "file_size_bytes": 25, "bits_represented": 200,
                       "theoretical_capacity_bits": 200, "bits_per_nucleotide": 2}
    summary = generate_benchmark_summary(original_stats, None, correction_stats, None)
    assert summary["recovery_confirmed"] is False


def test_summary_shortest_stage_picks_minimum_available_length():
    original_stats = {"dna_length": 100, "file_size_bytes": 25, "bits_represented": 200,
                       "theoretical_capacity_bits": 200, "bits_per_nucleotide": 2}
    mutation_stats = {"original_length": 100, "mutated_length": 40, "substitutions": 0,
                       "insertions": 0, "deletions": 60, "mutation_rate": 50}
    summary = generate_benchmark_summary(original_stats, mutation_stats, None, None)
    assert summary["shortest_stage"] == "Mutated"
    assert summary["shortest_length"] == 40


def test_summary_shortest_stage_none_when_nothing_available():
    summary = generate_benchmark_summary(None, None, None, None)
    assert summary["shortest_stage"] is None
    assert summary["highest_overhead_percent"] is None
    assert summary["correction_restored_length"] is None
    assert summary["recovery_confirmed"] is False
