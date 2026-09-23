"""
Tests for app/modules/capacity_analysis.py (Phase 19).

Covers information-theory basics, file-size conversion, theoretical
DNA-length math, actual-vs-theoretical comparison, redundancy/error-
correction overhead reuse, the physical-mass estimate, the cost
estimator, scale examples (verified NOT to allocate huge strings),
edge cases, and Phase 14 content-hash compatibility. Never asserts
exact timing.
"""

import tracemalloc

import pytest

from app.modules.capacity_analysis import (
    CapacityAnalysisError,
    BINARY_UNITS,
    bits_per_dna_base,
    bytes_per_dna_base,
    dna_bases_required_for_bits,
    dna_bases_required_for_bytes,
    digital_bytes_represented_by_dna_length,
    theoretical_density_summary,
    bytes_from_size,
    calculate_theoretical_dna_requirement,
    compare_actual_to_theoretical,
    calculate_copy_redundancy_overhead,
    calculate_error_correction_overhead,
    estimate_dna_mass,
    compare_to_conventional_storage,
    estimate_cost,
    generate_scale_examples,
)
from app.modules.result_identity import file_identity_matches


# --- Information theory ------------------------------------------------------------

def test_bits_per_dna_base_is_two():
    assert bits_per_dna_base() == 2.0


def test_bytes_per_dna_base_is_quarter_byte():
    assert bytes_per_dna_base() == 0.25


def test_bits_to_bases_conversion():
    assert dna_bases_required_for_bits(8) == 4.0
    assert dna_bases_required_for_bits(2) == 1.0


def test_bytes_to_bases_conversion():
    assert dna_bases_required_for_bytes(1) == 4.0
    assert dna_bases_required_for_bytes(1000) == 4000.0


def test_bases_to_bytes_conversion_is_inverse():
    assert digital_bytes_represented_by_dna_length(4) == 1.0
    assert digital_bytes_represented_by_dna_length(4000) == 1000.0


def test_theoretical_density_summary_structure():
    summary = theoretical_density_summary()
    assert summary["possible_bases"] == 4
    assert summary["bits_per_base"] == 2.0
    assert summary["bytes_per_base"] == 0.25
    assert summary["category"] == "theoretical"


# --- File-size conversion (binary units) --------------------------------------------

@pytest.mark.parametrize(
    "unit,expected_bytes",
    [
        ("B", 1),
        ("KB", 1024),
        ("MB", 1024**2),
        ("GB", 1024**3),
        ("TB", 1024**4),
        ("PB", 1024**5),
    ],
)
def test_bytes_from_size_each_unit(unit, expected_bytes):
    assert bytes_from_size(1, unit) == expected_bytes


def test_bytes_from_size_is_case_insensitive():
    assert bytes_from_size(1, "mb") == BINARY_UNITS["MB"]


def test_bytes_from_size_rejects_unknown_unit():
    with pytest.raises(CapacityAnalysisError):
        bytes_from_size(1, "XB")


def test_bytes_from_size_rejects_negative_value():
    with pytest.raises(CapacityAnalysisError):
        bytes_from_size(-1, "MB")


# --- DNA length: known theoretical relationship -------------------------------------

def test_one_byte_equals_four_theoretical_dna_bases():
    assert dna_bases_required_for_bytes(1) == 4


def test_calculate_theoretical_dna_requirement_for_one_kb():
    result = calculate_theoretical_dna_requirement(1, "KB")
    assert result["bytes"] == 1024
    assert result["theoretical_dna_bases"] == 4096
    assert result["category"] == "theoretical"


def test_calculate_theoretical_dna_requirement_for_one_mb():
    result = calculate_theoretical_dna_requirement(1, "MB")
    assert result["theoretical_dna_bases"] == 1024**2 * 4


# --- Actual vs. theoretical -----------------------------------------------------------

def test_compare_actual_to_theoretical_zero_overhead_case():
    # BioVault's real encoder never pads -- actual should always equal
    # theoretical exactly for this project's fixed 2-bit scheme.
    result = compare_actual_to_theoretical(1000, 4000)
    assert result["theoretical_dna_length"] == 4000
    assert result["additional_bases"] == 0
    assert result["encoding_overhead_percent"] == 0.0
    assert result["effective_bits_per_base"] == 2.0
    assert result["category"] == "measured_vs_theoretical"


def test_compare_actual_to_theoretical_positive_overhead_case():
    # A hypothetical actual length longer than theoretical (e.g. from a
    # different encoding scheme) must be reported honestly.
    result = compare_actual_to_theoretical(1000, 5000)
    assert result["additional_bases"] == 1000
    assert result["encoding_overhead_percent"] > 0


def test_compare_actual_to_theoretical_handles_zero_dna_length():
    result = compare_actual_to_theoretical(0, 0)
    assert result["effective_bits_per_base"] == 0.0


def test_compare_actual_to_theoretical_rejects_invalid_actual_length():
    with pytest.raises(CapacityAnalysisError):
        compare_actual_to_theoretical(1000, -5)


# --- Redundancy overhead (reused from Phase 18) ---------------------------------------

def test_copy_redundancy_zero_extra_copies():
    result = calculate_copy_redundancy_overhead(1000, 0)
    assert result["storage_multiplier"] == 1
    assert result["overhead_percent"] == 0.0
    assert result["category"] == "theoretical"


def test_copy_redundancy_one_extra_copy():
    result = calculate_copy_redundancy_overhead(1000, 1)
    assert result["storage_multiplier"] == 2
    assert result["overhead_percent"] == 100.0


def test_copy_redundancy_two_extra_copies():
    result = calculate_copy_redundancy_overhead(1000, 2)
    assert result["storage_multiplier"] == 3
    assert result["overhead_percent"] == 200.0


def test_copy_redundancy_three_extra_copies():
    result = calculate_copy_redundancy_overhead(1000, 3)
    assert result["storage_multiplier"] == 4
    assert result["overhead_percent"] == 300.0


def test_copy_redundancy_rejects_negative_extra_copies():
    with pytest.raises(CapacityAnalysisError):
        calculate_copy_redundancy_overhead(1000, -1)


# --- Error-correction / coding overhead (reused from storage_analysis) ---------------

def test_error_correction_overhead_reuses_existing_formula():
    result = calculate_error_correction_overhead(1000, block_size=4, redundancy_size=2)
    assert result["num_blocks"] == 250
    assert result["redundancy_bases"] == 500
    assert result["category"] == "theoretical"


def test_error_correction_overhead_rejects_invalid_block_size():
    with pytest.raises(CapacityAnalysisError):
        calculate_error_correction_overhead(1000, block_size=0, redundancy_size=2)


# --- Physical mass estimate ------------------------------------------------------------

def test_estimate_dna_mass_known_input():
    result = estimate_dna_mass(1_000_000, copies=1, average_base_weight_daltons=330.0)
    assert result["total_bases"] == 1_000_000
    assert result["estimated_mass_grams"] > 0
    assert result["category"] == "estimated"
    assert len(result["assumptions"]) >= 2


def test_estimate_dna_mass_scales_with_copies():
    single = estimate_dna_mass(1000, copies=1)
    triple = estimate_dna_mass(1000, copies=3)
    assert triple["estimated_mass_grams"] == pytest.approx(single["estimated_mass_grams"] * 3)


def test_estimate_dna_mass_zero_bases_gives_zero_mass():
    result = estimate_dna_mass(0, copies=1)
    assert result["estimated_mass_grams"] == 0.0


def test_estimate_dna_mass_rejects_invalid_weight_assumption():
    with pytest.raises(CapacityAnalysisError):
        estimate_dna_mass(1000, average_base_weight_daltons=0)
    with pytest.raises(CapacityAnalysisError):
        estimate_dna_mass(1000, average_base_weight_daltons=-10)


def test_estimate_dna_mass_rejects_invalid_copies():
    with pytest.raises(CapacityAnalysisError):
        estimate_dna_mass(1000, copies=0)


# --- Conventional storage comparison ----------------------------------------------------

def test_compare_to_conventional_storage_structure():
    rows = compare_to_conventional_storage()
    assert len(rows) == 4
    for row in rows:
        assert row["theoretical_dna_bases"] == dna_bases_required_for_bytes(row["digital_size_bytes"])
        assert row["category"] == "theoretical"


def test_compare_to_conventional_storage_accepts_custom_sizes():
    rows = compare_to_conventional_storage({"custom": 2048})
    assert len(rows) == 1
    assert rows[0]["theoretical_dna_bases"] == 8192


# --- Cost estimator -----------------------------------------------------------------------

def test_estimate_cost_user_defined_assumptions():
    result = estimate_cost(2_000_000, cost_per_million_bases_synthesis=100, cost_per_million_bases_sequencing=50)
    assert result["estimated_synthesis_cost"] == 200.0
    assert result["estimated_sequencing_cost"] == 100.0
    assert result["total_illustrative_cost"] == 300.0
    assert result["category"] == "estimated"


def test_estimate_cost_zero_cost():
    result = estimate_cost(1_000_000)
    assert result["total_illustrative_cost"] == 0.0


def test_estimate_cost_multiple_components_sum_correctly():
    result = estimate_cost(1_000_000, cost_per_million_bases_synthesis=10, cost_per_million_bases_sequencing=5, other_cost=3.5)
    assert result["total_illustrative_cost"] == 18.5


def test_estimate_cost_is_deterministic():
    first = estimate_cost(3_000_000, cost_per_million_bases_synthesis=7, other_cost=1)
    second = estimate_cost(3_000_000, cost_per_million_bases_synthesis=7, other_cost=1)
    assert first == second


def test_estimate_cost_rejects_negative_inputs():
    with pytest.raises(CapacityAnalysisError):
        estimate_cost(-1)
    with pytest.raises(CapacityAnalysisError):
        estimate_cost(1000, cost_per_million_bases_synthesis=-1)


def test_estimate_cost_includes_disclaimer():
    result = estimate_cost(1000)
    assert "not a current market quote" in result["disclaimer"]


# --- Scale examples: large-scale math without materializing huge strings ------------------

def test_generate_scale_examples_default_labels():
    rows = generate_scale_examples()
    labels = {row["label"] for row in rows}
    assert labels == {"1 MB file", "1 GB file", "1 TB data", "1 PB data"}


def test_generate_scale_examples_pb_scale_does_not_allocate_large_memory():
    tracemalloc.start()
    try:
        rows = generate_scale_examples(extra_copies=3)
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    pb_row = next(row for row in rows if row["label"] == "1 PB data")
    assert pb_row["theoretical_dna_bases"] > 0
    # A real PB-scale DNA string would need petabytes of memory; this
    # calculation must stay in the kilobytes range (pure arithmetic).
    assert peak < 10 * 1024 * 1024  # under 10 MB


def test_generate_scale_examples_redundancy_adjustment():
    rows = generate_scale_examples(extra_copies=1)
    mb_row = next(row for row in rows if row["label"] == "1 MB file")
    assert mb_row["redundancy_adjusted_bases"] == mb_row["theoretical_dna_bases"] * 2


# --- Edge cases -------------------------------------------------------------------------

def test_zero_bytes_produces_zero_bases():
    assert dna_bases_required_for_bytes(0) == 0


def test_one_byte_case():
    assert dna_bases_required_for_bytes(1) == 4


def test_empty_dna_length_produces_zero_bytes():
    assert digital_bytes_represented_by_dna_length(0) == 0


def test_very_large_integer_values_do_not_crash():
    huge_bytes = 10**18
    result = dna_bases_required_for_bytes(huge_bytes)
    assert result == huge_bytes * 4


def test_negative_values_are_rejected():
    with pytest.raises(CapacityAnalysisError):
        dna_bases_required_for_bytes(-1)
    with pytest.raises(CapacityAnalysisError):
        dna_bases_required_for_bits(-1)
    with pytest.raises(CapacityAnalysisError):
        digital_bytes_represented_by_dna_length(-1)


def test_invalid_unit_is_rejected():
    with pytest.raises(CapacityAnalysisError):
        calculate_theoretical_dna_requirement(1, "not_a_unit")


# --- Phase 14 content-hash compatibility ------------------------------------------------

def test_same_filename_same_hash_is_accepted():
    file_info = {"filename": "sample.txt", "content_hash": "hash-a"}
    stored = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert file_identity_matches(file_info, stored) is True


def test_same_filename_different_hash_is_rejected():
    file_info = {"filename": "sample.txt", "content_hash": "hash-b"}
    stored = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert file_identity_matches(file_info, stored) is False


def test_missing_hash_result_is_unverifiable():
    file_info = {"filename": "sample.txt", "content_hash": "hash-a"}
    legacy_stored = {"source_filename": "sample.txt"}
    assert file_identity_matches(file_info, legacy_stored) is False


# --- No mutation of input data ------------------------------------------------------------

def test_functions_do_not_mutate_input_dicts():
    sizes = {"1 TB": 1024**4}
    sizes_copy = dict(sizes)
    compare_to_conventional_storage(sizes)
    assert sizes == sizes_copy
