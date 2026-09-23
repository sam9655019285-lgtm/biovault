"""
Tests for app/modules/dna_mutator.py.

Plain-Python tests (no Streamlit). Randomized behaviors are made
deterministic with a fixed `seed` so results are reproducible.
Run with:  python -m pytest
"""

import pytest

from app.modules.dna_mutator import (
    DNAMutationError,
    VALID_BASES_SET,
    validate_dna_sequence,
    validate_mutation_rate,
    substitute_bases,
    insert_bases,
    delete_bases,
    mutate_dna,
    get_mutation_statistics,
)


# 1. Valid DNA validation -----------------------------------------------------

def test_valid_dna_sequence_is_accepted():
    assert validate_dna_sequence("ACGT") == "ACGT"


# 2. Empty DNA rejection --------------------------------------------------------

def test_empty_dna_sequence_is_rejected():
    with pytest.raises(DNAMutationError):
        validate_dna_sequence("")


# 3. Invalid character rejection -------------------------------------------------

def test_invalid_character_is_rejected():
    with pytest.raises(DNAMutationError):
        validate_dna_sequence("ACGTX")


# 4. Lowercase DNA conversion ------------------------------------------------------

def test_lowercase_dna_is_converted_to_uppercase():
    assert validate_dna_sequence("acgt") == "ACGT"


# 5. Invalid mutation-rate rejection ------------------------------------------------

@pytest.mark.parametrize("bad_rate", [-1, 101, -0.5, 150])
def test_invalid_mutation_rate_is_rejected(bad_rate):
    with pytest.raises(DNAMutationError):
        validate_mutation_rate(bad_rate)


def test_non_numeric_mutation_rate_is_rejected():
    with pytest.raises(DNAMutationError):
        validate_mutation_rate("high")  # type: ignore[arg-type]


def test_boundary_mutation_rates_are_accepted():
    assert validate_mutation_rate(0) == 0.0
    assert validate_mutation_rate(100) == 100.0


# 6. Zero-rate substitution returns the original sequence ----------------------------

def test_zero_rate_substitution_returns_unchanged_sequence():
    mutated, count = substitute_bases("ACGTACGT", mutation_rate=0, seed=1)
    assert mutated == "ACGTACGT"
    assert count == 0


# 7. Zero-rate insertion returns the original sequence --------------------------------

def test_zero_rate_insertion_returns_unchanged_sequence():
    mutated, count = insert_bases("ACGTACGT", mutation_rate=0, seed=1)
    assert mutated == "ACGTACGT"
    assert count == 0


# 8. Zero-rate deletion returns the original sequence ----------------------------------

def test_zero_rate_deletion_returns_unchanged_sequence():
    mutated, count = delete_bases("ACGTACGT", mutation_rate=0, seed=1)
    assert mutated == "ACGTACGT"
    assert count == 0


# 9. Substitution keeps the same length ---------------------------------------------------

def test_substitution_preserves_sequence_length():
    original = "ACGTACGTACGTACGT"
    mutated, _ = substitute_bases(original, mutation_rate=50, seed=7)
    assert len(mutated) == len(original)


# 10. Substitution produces only A, T, G, and C ----------------------------------------------

def test_substitution_output_contains_only_valid_bases():
    original = "ACGTACGTACGTACGT"
    mutated, _ = substitute_bases(original, mutation_rate=80, seed=3)
    assert set(mutated) <= VALID_BASES_SET


def test_substitution_never_replaces_a_base_with_itself():
    # With a 100% rate, every base must change to a *different* base.
    original = "AAAAAAAAAA"
    mutated, count = substitute_bases(original, mutation_rate=100, seed=9)
    assert count == len(original)
    assert all(base != "A" for base in mutated)


# 11. Insertion produces valid DNA characters -------------------------------------------------

def test_insertion_output_contains_only_valid_bases():
    original = "ACGTACGT"
    mutated, _ = insert_bases(original, mutation_rate=90, seed=5)
    assert set(mutated) <= VALID_BASES_SET


# 12. Deletion produces valid DNA characters ---------------------------------------------------

def test_deletion_output_contains_only_valid_bases():
    original = "ACGTACGT"
    mutated, _ = delete_bases(original, mutation_rate=50, seed=5)
    assert set(mutated) <= VALID_BASES_SET


def test_deletion_length_never_negative_even_at_full_rate():
    mutated, count = delete_bases("ACGTACGT", mutation_rate=100, seed=2)
    assert mutated == ""
    assert count == 8
    assert len(mutated) >= 0


# 13. Insertion and deletion change sequence length when mutations occur ------------------------

def test_insertion_increases_length_when_mutations_occur():
    original = "ACGTACGTACGTACGTACGT"
    mutated, count = insert_bases(original, mutation_rate=100, seed=1)
    assert count > 0
    assert len(mutated) > len(original)


def test_deletion_decreases_length_when_mutations_occur():
    original = "ACGTACGTACGTACGTACGT"
    mutated, count = delete_bases(original, mutation_rate=100, seed=1)
    assert count > 0
    assert len(mutated) < len(original)


# 14. Same seed produces the same result -----------------------------------------------------

def test_same_seed_produces_identical_substitution_result():
    original = "ACGTACGTACGTACGT"
    result_a, count_a = substitute_bases(original, mutation_rate=40, seed=99)
    result_b, count_b = substitute_bases(original, mutation_rate=40, seed=99)
    assert result_a == result_b
    assert count_a == count_b


def test_same_seed_produces_identical_insertion_result():
    original = "ACGTACGT"
    result_a, _ = insert_bases(original, mutation_rate=40, seed=21)
    result_b, _ = insert_bases(original, mutation_rate=40, seed=21)
    assert result_a == result_b


def test_same_seed_produces_identical_deletion_result():
    original = "ACGTACGT"
    result_a, _ = delete_bases(original, mutation_rate=40, seed=21)
    result_b, _ = delete_bases(original, mutation_rate=40, seed=21)
    assert result_a == result_b


def test_different_seeds_can_produce_different_results():
    original = "ACGTACGTACGTACGTACGTACGTACGT"
    result_a, _ = substitute_bases(original, mutation_rate=50, seed=1)
    result_b, _ = substitute_bases(original, mutation_rate=50, seed=2)
    assert result_a != result_b


# 15. Mutation statistics are calculated correctly ---------------------------------------------

def test_mutation_statistics_total_and_rate():
    stats = get_mutation_statistics(
        original_length=100,
        mutated_length=105,
        substitutions=3,
        insertions=5,
        deletions=0,
    )
    assert stats["total_edits"] == 8
    assert stats["edit_rate_percent"] == 8.0
    assert stats["original_length"] == 100
    assert stats["mutated_length"] == 105


def test_mutation_statistics_handles_zero_length_gracefully():
    stats = get_mutation_statistics(original_length=0, mutated_length=0)
    assert stats["total_edits"] == 0
    assert stats["edit_rate_percent"] == 0.0


# 16. All mutation types are accepted ------------------------------------------------------------

@pytest.mark.parametrize("mutation_type", ["substitution", "insertion", "deletion"])
def test_mutate_dna_accepts_all_mutation_types(mutation_type):
    result = mutate_dna("ACGTACGTACGT", mutation_type, mutation_rate=20, seed=4)
    assert result["mutation_type"] == mutation_type
    assert set(result["mutated_sequence"]) <= VALID_BASES_SET
    assert "total_edits" in result
    assert "edit_rate_percent" in result


# 17. Invalid mutation type is rejected -----------------------------------------------------------

def test_invalid_mutation_type_is_rejected():
    with pytest.raises(DNAMutationError):
        mutate_dna("ACGT", "duplication", mutation_rate=10, seed=1)


# Extra: mutate_dna end-to-end statistics sanity check ----------------------------------------------

def test_mutate_dna_substitution_statistics_are_consistent():
    original = "ACGTACGTACGTACGTACGT"
    result = mutate_dna(original, "substitution", mutation_rate=100, seed=1)
    assert result["mutated_length"] == len(original)
    assert result["substitutions"] == len(original)
    assert result["insertions"] == 0
    assert result["deletions"] == 0
    assert result["total_edits"] == len(original)
