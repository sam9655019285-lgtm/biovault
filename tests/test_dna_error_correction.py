"""
Tests for app/modules/dna_error_correction.py.

Plain-Python tests (no Streamlit). The correction algorithm itself is
fully deterministic (no randomness), so results are reproducible by
construction -- errors are injected manually via string slicing to
create precise, controlled test scenarios.
Run with:  python -m pytest
"""

import pytest

from app.modules.dna_error_correction import (
    DNAErrorCorrectionError,
    validate_dna_sequence,
    add_redundancy,
    detect_errors,
    correct_substitution_errors,
    remove_redundancy,
    VALID_BASES_SET,
)


def _flip_base(sequence: str, index: int, new_base: str) -> str:
    """Test helper: replace a single character at `index` in `sequence`."""
    return sequence[:index] + new_base + sequence[index + 1 :]


# 1. Valid DNA validation -----------------------------------------------------

def test_valid_dna_sequence_is_accepted():
    assert validate_dna_sequence("acgtACGT") == "ACGTACGT"


# 2. Empty DNA rejection --------------------------------------------------------

def test_empty_dna_sequence_is_rejected():
    with pytest.raises(DNAErrorCorrectionError):
        validate_dna_sequence("")


# 3. Invalid DNA character rejection ----------------------------------------------

def test_invalid_dna_character_is_rejected():
    with pytest.raises(DNAErrorCorrectionError):
        validate_dna_sequence("ACGTX")


# 4. Invalid block size rejection --------------------------------------------------

@pytest.mark.parametrize("bad_block_size", [0, -1, 1.5, "4"])
def test_invalid_block_size_is_rejected(bad_block_size):
    with pytest.raises(DNAErrorCorrectionError):
        add_redundancy("ACGTACGT", block_size=bad_block_size, redundancy_size=2)


def test_block_size_over_max_is_rejected():
    with pytest.raises(DNAErrorCorrectionError):
        add_redundancy("ACGTACGT", block_size=99999, redundancy_size=2)


# 5. Invalid redundancy size rejection -----------------------------------------------

@pytest.mark.parametrize("bad_redundancy_size", [0, -1, 2.5, "2"])
def test_invalid_redundancy_size_is_rejected(bad_redundancy_size):
    with pytest.raises(DNAErrorCorrectionError):
        add_redundancy("ACGTACGT", block_size=4, redundancy_size=bad_redundancy_size)


# 6. Redundancy generation ------------------------------------------------------------

def test_add_redundancy_produces_expected_structure():
    result = add_redundancy("ACGTACGT", block_size=4, redundancy_size=2)
    # 2 blocks of 4 bases each, plus 2 redundancy bases per block = 8 + 4 = 12
    assert result["original_length"] == 8
    assert len(result["protected_sequence"]) == 8 + 2 * 2
    assert set(result["protected_sequence"]) <= VALID_BASES_SET


def test_add_redundancy_handles_final_partial_block():
    # 10 bases with block_size=4 -> blocks of 4, 4, 2 (no padding).
    result = add_redundancy("ACGTACGTAC", block_size=4, redundancy_size=1)
    assert result["original_length"] == 10
    # 3 blocks -> 3 redundancy bases added.
    assert len(result["protected_sequence"]) == 10 + 3


# 7. Checksum generation ---------------------------------------------------------------

def test_checksum_is_deterministic_for_same_block():
    result_a = add_redundancy("ACGT", block_size=4, redundancy_size=1)
    result_b = add_redundancy("ACGT", block_size=4, redundancy_size=1)
    assert result_a["protected_sequence"] == result_b["protected_sequence"]


def test_checksum_base_is_repeated_redundancy_size_times():
    result = add_redundancy("AAAA", block_size=4, redundancy_size=3)
    # Block "AAAA" -> checksum value 0 -> base "A"; redundancy = "AAA".
    protected = result["protected_sequence"]
    assert protected == "AAAA" + "AAA"


# 8. No-error detection --------------------------------------------------------------------

def test_detect_errors_finds_nothing_on_unmutated_sequence():
    protection = add_redundancy("ACGTACGTACGT", block_size=4, redundancy_size=2)
    detection = detect_errors(
        protection["protected_sequence"], block_size=4, redundancy_size=2,
        original_length=protection["original_length"],
    )
    assert detection["length_matches_expected"]
    assert detection["errors_detected"] == 0
    assert detection["error_block_indices"] == []


# 9. Detection of a single substitution error ------------------------------------------------

def test_detect_errors_finds_single_substitution():
    protection = add_redundancy("ACGTACGT", block_size=4, redundancy_size=2)
    protected = protection["protected_sequence"]

    # Flip the first base of the first block to something different.
    original_first_base = protected[0]
    new_base = next(b for b in VALID_BASES_SET if b != original_first_base)
    corrupted = _flip_base(protected, 0, new_base)

    detection = detect_errors(
        corrupted, block_size=4, redundancy_size=2, original_length=protection["original_length"]
    )
    assert detection["length_matches_expected"]
    assert detection["errors_detected"] == 1
    assert detection["error_block_indices"] == [0]


# 10. Correction of a correctable substitution error --------------------------------------------

def test_single_substitution_is_corrected_with_small_block_size():
    # block_size=1 makes the checksum equal to the base's own value,
    # so a single substitution is always uniquely correctable.
    original = "ACGT"
    protection = add_redundancy(original, block_size=1, redundancy_size=3)
    protected = protection["protected_sequence"]

    # Corrupt the data base of the second block (position 4 in the
    # protected sequence: block0(1)+red0(3)=4, then block1 starts at 4).
    corrupted = _flip_base(protected, 4, "T" if protected[4] != "T" else "A")

    correction = correct_substitution_errors(
        corrupted, block_size=1, redundancy_size=3, original_length=protection["original_length"]
    )
    assert correction["errors_detected"] == 1
    assert correction["errors_corrected"] == 1
    assert correction["uncorrectable_errors"] == 0
    assert correction["correction_success"] is True
    assert correction["corrected_sequence"] == original


# 11. Uncorrectable error handling -------------------------------------------------------------

def test_multiple_errors_in_one_block_are_handled_honestly():
    # A larger block with two substitutions overwhelms this simple
    # mod-4 checksum: sometimes no single-flip fix matches (correctly
    # reported as uncorrectable), and sometimes -- because the checksum
    # only has 4 possible values -- a single-flip fix coincidentally
    # matches anyway, producing a *wrong* but "confident" correction.
    # This is a documented limitation of the method, not a bug. What
    # must always hold is the bookkeeping: every detected error is
    # accounted for as either corrected or uncorrectable, and success
    # is only claimed when nothing was left uncorrectable.
    original = "ACGTACGTACGT"  # 12 bases, one block of 12
    protection = add_redundancy(original, block_size=12, redundancy_size=2)
    protected = protection["protected_sequence"]

    # Corrupt two different positions within the single block.
    corrupted = _flip_base(protected, 0, "T" if protected[0] != "T" else "A")
    corrupted = _flip_base(corrupted, 5, "G" if corrupted[5] != "G" else "C")

    correction = correct_substitution_errors(
        corrupted, block_size=12, redundancy_size=2, original_length=protection["original_length"]
    )
    assert correction["errors_corrected"] + correction["uncorrectable_errors"] == correction["errors_detected"]
    if correction["uncorrectable_errors"] > 0:
        assert correction["correction_success"] is False
    if correction["correction_success"]:
        assert correction["uncorrectable_errors"] == 0


def test_ambiguous_redundancy_tie_is_reported_uncorrectable():
    # redundancy_size=2 with the two checksum copies disagreeing has no
    # clear majority -- the intended checksum can't be determined, so
    # this must be reported as uncorrectable rather than guessed at.
    protection = add_redundancy("ACGT", block_size=4, redundancy_size=2)
    protected = protection["protected_sequence"]
    # protected = block(4 chars) + checksum*2; corrupt one checksum copy
    # so the two redundancy characters disagree (a tie).
    checksum_char = protected[4]
    other_base = next(b for b in VALID_BASES_SET if b != checksum_char)
    tied = _flip_base(protected, 5, other_base)

    correction = correct_substitution_errors(
        tied, block_size=4, redundancy_size=2, original_length=protection["original_length"]
    )
    assert correction["uncorrectable_errors"] == 1
    assert correction["correction_success"] is False


# 12. Invalid DNA length handling ----------------------------------------------------------------

def test_length_mismatch_is_reported_not_guessed():
    protection = add_redundancy("ACGTACGT", block_size=4, redundancy_size=2)
    # Simulate an insertion by adding one extra base.
    tampered = protection["protected_sequence"] + "A"

    detection = detect_errors(
        tampered, block_size=4, redundancy_size=2, original_length=protection["original_length"]
    )
    assert detection["length_matches_expected"] is False
    assert detection["errors_detected"] is None

    correction = correct_substitution_errors(
        tampered, block_size=4, redundancy_size=2, original_length=protection["original_length"]
    )
    assert correction["correction_success"] is False
    assert correction["corrected_sequence"] is None


# 13. No invalid DNA characters in generated output ------------------------------------------------

def test_protected_and_corrected_sequences_contain_only_valid_bases():
    original = "ACGTACGTACGTACGT"
    protection = add_redundancy(original, block_size=4, redundancy_size=2)
    assert set(protection["protected_sequence"]) <= VALID_BASES_SET

    correction = correct_substitution_errors(
        protection["protected_sequence"], block_size=4, redundancy_size=2,
        original_length=protection["original_length"],
    )
    assert set(correction["corrected_sequence"]) <= VALID_BASES_SET


# 14. Zero-error sequence remains unchanged after correction -----------------------------------------

def test_zero_error_sequence_unchanged_after_correction():
    original = "ACGTACGTACGT"
    protection = add_redundancy(original, block_size=4, redundancy_size=2)

    correction = correct_substitution_errors(
        protection["protected_sequence"], block_size=4, redundancy_size=2,
        original_length=protection["original_length"],
    )
    assert correction["errors_detected"] == 0
    assert correction["errors_corrected"] == 0
    assert correction["correction_success"] is True
    assert correction["corrected_sequence"] == original


# 15. Correction result contains required metadata --------------------------------------------------

def test_correction_result_contains_required_metadata_fields():
    protection = add_redundancy("ACGTACGT", block_size=4, redundancy_size=2)
    correction = correct_substitution_errors(
        protection["protected_sequence"], block_size=4, redundancy_size=2,
        original_length=protection["original_length"],
    )
    required_fields = {
        "received_sequence",
        "corrected_sequence",
        "blocks_checked",
        "errors_detected",
        "errors_corrected",
        "uncorrectable_errors",
        "correction_success",
        "message",
    }
    assert required_fields <= set(correction.keys())


# 16. Deterministic results for the same input -----------------------------------------------------

def test_correction_is_deterministic_for_same_input():
    protection = add_redundancy("ACGTACGTACGT", block_size=4, redundancy_size=2)
    protected = protection["protected_sequence"]
    corrupted = _flip_base(protected, 0, "T" if protected[0] != "T" else "A")

    result_a = correct_substitution_errors(
        corrupted, block_size=4, redundancy_size=2, original_length=protection["original_length"]
    )
    result_b = correct_substitution_errors(
        corrupted, block_size=4, redundancy_size=2, original_length=protection["original_length"]
    )
    assert result_a == result_b


# Extra: remove_redundancy round-trips a clean protected sequence -----------------------------------

def test_remove_redundancy_recovers_original_when_no_errors():
    original = "ACGTACGTACGT"
    protection = add_redundancy(original, block_size=4, redundancy_size=2)
    recovered = remove_redundancy(
        protection["protected_sequence"], block_size=4, redundancy_size=2,
        original_length=protection["original_length"],
    )
    assert recovered == original


def test_remove_redundancy_rejects_length_mismatch():
    protection = add_redundancy("ACGTACGT", block_size=4, redundancy_size=2)
    tampered = protection["protected_sequence"][:-1]  # simulate a deletion
    with pytest.raises(DNAErrorCorrectionError):
        remove_redundancy(
            tampered, block_size=4, redundancy_size=2,
            original_length=protection["original_length"],
        )
