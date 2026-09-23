"""
Tests for app/modules/performance_analysis.py (Phase 15).

These tests check STRUCTURE and CORRECTNESS -- never exact timing
values, since execution time is inherently machine-dependent. All
tests use the smallest size preset (or smaller) so the suite stays
fast and deterministic.
"""

import pytest

from app.modules.performance_analysis import (
    PerformanceAnalysisError,
    SIZE_PRESETS,
    MEASUREMENT_LABEL,
    generate_deterministic_bytes,
    measure_time,
    measure_time_and_memory,
    run_encoding_benchmark,
    run_decoding_benchmark,
    run_mutation_benchmark,
    run_error_correction_benchmark,
    run_storage_analysis_benchmark,
    run_full_benchmark_suite,
    compare_size_presets,
)
from app.modules.dna_encoder import encode_file_to_dna
from app.modules.dna_decoder import decode_dna_to_file


# --- Deterministic test-data generation ---------------------------------------

def test_generate_deterministic_bytes_same_seed_same_output():
    a = generate_deterministic_bytes(256, seed=42)
    b = generate_deterministic_bytes(256, seed=42)
    assert a == b


def test_generate_deterministic_bytes_different_seed_different_output():
    a = generate_deterministic_bytes(256, seed=1)
    b = generate_deterministic_bytes(256, seed=2)
    assert a != b


def test_generate_deterministic_bytes_correct_size():
    for size in (0, 1, 100, 1024):
        assert len(generate_deterministic_bytes(size)) == size


def test_generate_deterministic_bytes_rejects_negative_size():
    with pytest.raises(PerformanceAnalysisError):
        generate_deterministic_bytes(-1)


def test_generate_deterministic_bytes_rejects_non_int_size():
    with pytest.raises(PerformanceAnalysisError):
        generate_deterministic_bytes(1.5)  # type: ignore[arg-type]
    with pytest.raises(PerformanceAnalysisError):
        generate_deterministic_bytes(True)  # type: ignore[arg-type]


# --- Size presets --------------------------------------------------------------

def test_size_presets_are_small_medium_large_and_reasonable():
    assert len(SIZE_PRESETS) == 3
    sizes = list(SIZE_PRESETS.values())
    # Strictly increasing: small < medium < large.
    assert sizes[0] < sizes[1] < sizes[2]
    # The largest preset must stay well under a size that could freeze
    # the interface or exhaust memory (kept comfortably below 5 MB, the
    # project's own upload limit).
    assert sizes[-1] <= 5 * 1024 * 1024


# --- measure_time / measure_time_and_memory -----------------------------------

def test_measure_time_returns_result_and_non_negative_elapsed():
    result, elapsed = measure_time(sum, [1, 2, 3])
    assert result == 6
    assert elapsed >= 0


def test_measure_time_and_memory_returns_result_elapsed_and_memory():
    result, elapsed, peak_memory = measure_time_and_memory(sum, range(1000))
    assert result == sum(range(1000))
    assert elapsed >= 0
    assert peak_memory >= 0


# --- Individual benchmark functions: structure + correctness ------------------

def test_run_encoding_benchmark_structure_and_correctness():
    data = generate_deterministic_bytes(64)
    result = run_encoding_benchmark(data)

    assert result["operation"] == "Encoding"
    assert result["input_size_bytes"] == 64
    assert result["output_dna_length"] == 64 * 4  # 4 bases per byte, always exact
    assert result["elapsed_seconds"] >= 0
    assert result["peak_memory_bytes"] >= 0
    assert result["note"] == MEASUREMENT_LABEL


def test_run_decoding_benchmark_structure_and_correctness():
    data = generate_deterministic_bytes(64)
    dna_sequence = encode_file_to_dna(data)["dna_sequence"]
    result = run_decoding_benchmark(dna_sequence)

    assert result["operation"] == "Decoding"
    assert result["input_dna_length"] == len(dna_sequence)
    assert result["output_size_bytes"] == 64
    assert result["elapsed_seconds"] >= 0
    assert result["note"] == MEASUREMENT_LABEL


def test_encode_then_decode_via_benchmarks_recovers_original_bytes():
    """The benchmark wrappers must not change correctness -- round-trip
    recovery must still work exactly as the underlying pipeline promises."""
    data = generate_deterministic_bytes(128, seed=7)
    encoding_result = run_encoding_benchmark(data)
    dna_sequence = encode_file_to_dna(data)["dna_sequence"]
    assert len(dna_sequence) == encoding_result["output_dna_length"]

    decoded = decode_dna_to_file(dna_sequence)
    assert decoded["recovered_bytes"] == data


def test_run_mutation_benchmark_structure():
    dna_sequence = encode_file_to_dna(generate_deterministic_bytes(64))["dna_sequence"]
    result = run_mutation_benchmark(dna_sequence, "substitution", 10.0, seed=1)

    assert result["operation"] == "Mutation"
    assert result["input_dna_length"] == len(dna_sequence)
    assert result["output_dna_length"] == len(dna_sequence)  # substitution preserves length
    assert result["elapsed_seconds"] >= 0
    assert result["note"] == MEASUREMENT_LABEL


def test_run_error_correction_benchmark_structure():
    dna_sequence = encode_file_to_dna(generate_deterministic_bytes(64))["dna_sequence"]
    result = run_error_correction_benchmark(dna_sequence)

    assert result["operation"] == "Error Correction"
    assert result["input_dna_length"] == len(dna_sequence)
    assert result["protected_dna_length"] > result["input_dna_length"]  # redundancy adds bases
    assert result["elapsed_seconds"] >= 0
    assert result["note"] == MEASUREMENT_LABEL


def test_run_storage_analysis_benchmark_structure():
    result = run_storage_analysis_benchmark(64, 256)

    assert result["operation"] == "Storage Analysis"
    assert result["raw_efficiency_percent"] == 100.0
    assert result["elapsed_seconds"] >= 0
    assert result["note"] == MEASUREMENT_LABEL


# --- Full benchmark suite ------------------------------------------------------

def test_run_full_benchmark_suite_small_input_structure():
    result = run_full_benchmark_suite(256)  # well below even the Small preset

    assert result["input_size_bytes"] == 256
    assert result["encoding"]["operation"] == "Encoding"
    assert result["decoding"]["operation"] == "Decoding"
    assert result["mutation"]["operation"] == "Mutation"
    assert result["correction"]["operation"] == "Error Correction"
    assert result["storage"]["operation"] == "Storage Analysis"
    assert result["total_elapsed_seconds"] >= 0
    assert result["note"] == MEASUREMENT_LABEL


def test_run_full_benchmark_suite_handles_empty_input_safely():
    # An empty file is a valid (if edge-case) input -- must not crash.
    result = run_full_benchmark_suite(0)
    assert result["encoding"]["output_dna_length"] == 0
    # Decoding/mutation/correction all require a non-empty DNA sequence
    # -- the benchmark must skip them gracefully rather than letting
    # their own "nothing to decode/mutate/protect" validation raise.
    assert result["decoding"] is None
    assert result["mutation"] is None
    assert result["correction"] is None
    assert result["storage"] is not None  # storage math handles 0 safely on its own


def test_run_full_benchmark_suite_rejects_negative_size():
    with pytest.raises(PerformanceAnalysisError):
        run_full_benchmark_suite(-5)


def test_compare_size_presets_returns_one_entry_per_preset():
    # Use tiny stand-in presets so this test stays fast regardless of
    # the real SIZE_PRESETS values.
    tiny_presets = {"Tiny A": 16, "Tiny B": 32}
    results = compare_size_presets(tiny_presets)

    assert len(results) == 2
    assert results[0]["label"] == "Tiny A"
    assert results[0]["input_size_bytes"] == 16
    assert results[1]["label"] == "Tiny B"
    assert results[1]["input_size_bytes"] == 32


# --- No modification of original input data -----------------------------------

def test_generate_deterministic_bytes_output_is_immutable_type():
    # bytes (not bytearray) can never be mutated in place by later code.
    data = generate_deterministic_bytes(32)
    assert isinstance(data, bytes)


def test_benchmark_does_not_mutate_input_bytes():
    data = generate_deterministic_bytes(64, seed=3)
    original_copy = bytes(data)
    run_encoding_benchmark(data)
    assert data == original_copy


# --- Compatibility with Phase 14 content-hash identity checks ------------------

def test_benchmark_generated_data_is_compatible_with_content_hash():
    from app.modules.file_handler import compute_content_hash

    data = generate_deterministic_bytes(128, seed=9)
    # Hashing benchmark-generated bytes must work exactly like hashing
    # any other file's bytes -- no special-casing, no crash.
    digest_a = compute_content_hash(data)
    digest_b = compute_content_hash(generate_deterministic_bytes(128, seed=9))
    assert digest_a == digest_b  # same seed -> same bytes -> same hash

    digest_c = compute_content_hash(generate_deterministic_bytes(128, seed=10))
    assert digest_a != digest_c  # different seed -> different bytes -> different hash
