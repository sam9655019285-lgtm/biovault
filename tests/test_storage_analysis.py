"""
Tests for app/modules/storage_analysis.py.

Plain-Python tests (no Streamlit). All calculations here are pure
arithmetic, so results are fully deterministic.
Run with:  python -m pytest
"""

import pytest

from app.modules.storage_analysis import (
    StorageAnalysisError,
    calculate_binary_size,
    calculate_dna_size,
    calculate_dna_capacity,
    calculate_raw_efficiency,
    calculate_encoding_overhead,
    calculate_redundancy_overhead,
    calculate_mutation_impact,
    format_bytes,
    analyze_storage_efficiency,
)


# 1. Zero-byte file handling -----------------------------------------------

def test_zero_byte_file_produces_zero_sizes():
    result = calculate_binary_size(b"")
    assert result["size_bytes"] == 0
    assert result["size_bits"] == 0


# 2. Byte-to-bit conversion --------------------------------------------------

def test_byte_to_bit_conversion_is_times_eight():
    result = calculate_binary_size(b"AB")
    assert result["size_bytes"] == 2
    assert result["size_bits"] == 16


# 3. Binary size calculation -----------------------------------------------

def test_binary_size_rejects_non_bytes_input():
    with pytest.raises(StorageAnalysisError):
        calculate_binary_size("not bytes")  # type: ignore[arg-type]


# 4. DNA length calculation -----------------------------------------------

def test_dna_size_from_binary_bits():
    result = calculate_dna_size(64)  # 64 bits -> 32 bases
    assert result["dna_bases_required"] == 32


def test_dna_size_rejects_odd_bit_length():
    with pytest.raises(StorageAnalysisError):
        calculate_dna_size(7)


# 5. DNA capacity calculation ------------------------------------------------

def test_dna_capacity_calculation():
    result = calculate_dna_capacity(100)
    assert result["capacity_bits"] == 200
    assert result["capacity_bytes"] == 25.0


def test_dna_capacity_zero_length():
    result = calculate_dna_capacity(0)
    assert result["capacity_bits"] == 0
    assert result["capacity_bytes"] == 0


# 6. Raw efficiency calculation ------------------------------------------------

def test_raw_efficiency_is_100_percent_for_matched_sizes():
    # 800 data bits stored in 400 bases (800 bits of DNA capacity) -> 100%
    assert calculate_raw_efficiency(800, 800) == 100.0


def test_raw_efficiency_below_100_when_dna_capacity_is_larger():
    assert calculate_raw_efficiency(400, 800) == 50.0


# 7. Zero-length efficiency handling ------------------------------------------

def test_raw_efficiency_zero_length_does_not_crash():
    assert calculate_raw_efficiency(0, 0) == 0.0


# 8. Invalid negative values ----------------------------------------------------

@pytest.mark.parametrize(
    "func, args",
    [
        (calculate_dna_size, (-2,)),
        (calculate_dna_capacity, (-1,)),
        (calculate_raw_efficiency, (-1, 10)),
        (calculate_raw_efficiency, (10, -1)),
        (calculate_encoding_overhead, (-1, 10)),
    ],
)
def test_negative_values_are_rejected(func, args):
    with pytest.raises(StorageAnalysisError):
        func(*args)


def test_format_bytes_rejects_negative_value():
    with pytest.raises(StorageAnalysisError):
        format_bytes(-5)


def test_redundancy_overhead_rejects_negative_dna_length():
    with pytest.raises(StorageAnalysisError):
        calculate_redundancy_overhead(-10, block_size=4, redundancy_size=2)


def test_redundancy_overhead_rejects_invalid_block_size():
    with pytest.raises(StorageAnalysisError):
        calculate_redundancy_overhead(100, block_size=0, redundancy_size=2)


def test_redundancy_overhead_rejects_invalid_redundancy_size():
    with pytest.raises(StorageAnalysisError):
        calculate_redundancy_overhead(100, block_size=4, redundancy_size=0)


# 9. Redundancy overhead calculation --------------------------------------------

def test_redundancy_overhead_basic_case():
    # 100 bases, block_size=4 -> exactly 25 blocks, redundancy_size=2 -> 50 redundancy bases.
    result = calculate_redundancy_overhead(100, block_size=4, redundancy_size=2)
    assert result["num_blocks"] == 25
    assert result["redundancy_bases"] == 50
    assert result["protected_length"] == 150
    assert result["overhead_percent"] == 50.0


# 10. Block count calculation ----------------------------------------------------

def test_block_count_matches_expected_division():
    result = calculate_redundancy_overhead(40, block_size=10, redundancy_size=1)
    assert result["num_blocks"] == 4


# 11. Partial final block handling -----------------------------------------------

def test_partial_final_block_is_counted_as_a_full_block():
    # 10 bases with block_size=4 -> blocks of 4, 4, 2 -> 3 blocks total.
    result = calculate_redundancy_overhead(10, block_size=4, redundancy_size=1)
    assert result["num_blocks"] == 3
    assert result["redundancy_bases"] == 3


def test_redundancy_overhead_zero_dna_length():
    result = calculate_redundancy_overhead(0, block_size=4, redundancy_size=2)
    assert result["num_blocks"] == 0
    assert result["redundancy_bases"] == 0
    assert result["protected_length"] == 0
    assert result["overhead_percent"] == 0.0


# 12. Protected DNA length calculation --------------------------------------------

def test_protected_length_matches_dna_error_correction_module():
    # Cross-check against the real Phase 6 module to ensure the math
    # used here stays consistent with the actual redundancy algorithm.
    from app.modules.dna_error_correction import add_redundancy

    sequence = "ACGT" * 37  # 148 bases, deliberately not a clean multiple of most block sizes
    block_size, redundancy_size = 5, 3
    actual = add_redundancy(sequence, block_size, redundancy_size)
    predicted = calculate_redundancy_overhead(len(sequence), block_size, redundancy_size)

    assert len(actual["protected_sequence"]) == predicted["protected_length"]


# 13. Mutation impact calculation ------------------------------------------------

def test_mutation_impact_calculates_length_difference():
    stats = {
        "original_length": 100,
        "mutated_length": 108,
        "mutation_type": "insertion",
        "mutation_rate": 10,
        "total_edits": 8,
    }
    result = calculate_mutation_impact(stats)
    assert result["length_difference"] == 8
    assert result["length_changed"] is True


def test_mutation_impact_no_length_change_for_substitution():
    stats = {
        "original_length": 50,
        "mutated_length": 50,
        "mutation_type": "substitution",
        "mutation_rate": 20,
        "total_edits": 10,
    }
    result = calculate_mutation_impact(stats)
    assert result["length_difference"] == 0
    assert result["length_changed"] is False


def test_mutation_impact_rejects_incomplete_stats():
    with pytest.raises(StorageAnalysisError):
        calculate_mutation_impact({"original_length": 10})


# 14. Human-readable byte formatting -----------------------------------------------

@pytest.mark.parametrize(
    "num_bytes, expected_prefix",
    [
        (0, "0 B"),
        (512, "512 B"),
        (1024, "1.00 KB"),
        (1536, "1.50 KB"),
        (1024 * 1024, "1.00 MB"),
    ],
)
def test_format_bytes_human_readable(num_bytes, expected_prefix):
    assert format_bytes(num_bytes) == expected_prefix


# 15. Deterministic calculations -------------------------------------------------------

def test_analyze_storage_efficiency_is_deterministic():
    result_a = analyze_storage_efficiency(file_size_bytes=100, dna_length=400, block_size=4, redundancy_size=2)
    result_b = analyze_storage_efficiency(file_size_bytes=100, dna_length=400, block_size=4, redundancy_size=2)
    assert result_a == result_b


# 16. Required result fields ------------------------------------------------------------

def test_analyze_storage_efficiency_contains_required_sections():
    result = analyze_storage_efficiency(file_size_bytes=50, dna_length=200)
    required_keys = {
        "file_size_bytes",
        "binary_info",
        "dna_size_info",
        "capacity_info",
        "encoding_overhead",
        "raw_efficiency_percent",
        "redundancy_info",
        "mutation_info",
    }
    assert required_keys <= set(result.keys())
    # Without block/redundancy or mutation inputs, those sections are
    # explicitly None rather than fabricated.
    assert result["redundancy_info"] is None
    assert result["mutation_info"] is None


def test_analyze_storage_efficiency_includes_redundancy_and_mutation_when_given():
    mutation_stats = {
        "original_length": 20,
        "mutated_length": 20,
        "mutation_type": "substitution",
        "mutation_rate": 5,
        "total_edits": 1,
    }
    result = analyze_storage_efficiency(
        file_size_bytes=10, dna_length=40, block_size=4, redundancy_size=2, mutation_stats=mutation_stats
    )
    assert result["redundancy_info"] is not None
    assert result["mutation_info"] is not None


def test_analyze_storage_efficiency_accepts_raw_bytes_for_file_size():
    result = analyze_storage_efficiency(file_size_bytes=b"hello", dna_length=20)
    assert result["file_size_bytes"] == 5
