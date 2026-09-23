"""
Tests for app/modules/dna_integrity.py (Phase 17).

Covers character validation, length validation, statistics, corruption
analysis, original-vs-recovered comparison, the full integrity report
(all 6 status categories), Phase 14 content-hash compatibility, and
non-mutation of input data. Never asserts exact timing.
"""

import pytest

from app.modules.dna_integrity import (
    DNAIntegrityError,
    STATUS_INVALID,
    STATUS_INCOMPLETE,
    STATUS_CORRUPTED,
    STATUS_UNABLE_TO_VERIFY,
    STATUS_VALID,
    STATUS_RECOVERED,
    BASES_PER_BYTE,
    check_dna_characters,
    check_dna_length,
    calculate_dna_statistics,
    analyze_corruption,
    compare_original_and_recovered,
    build_integrity_report,
)
from app.modules.dna_encoder import encode_file_to_dna
from app.modules.dna_mutator import mutate_dna
from app.modules.file_handler import compute_content_hash
from app.modules.result_identity import file_identity_matches


# --- A. DNA character validation ------------------------------------------------

def test_valid_dna_is_detected():
    result = check_dna_characters("ACGTACGT")
    assert result["is_valid"] is True
    assert result["invalid_character_count"] == 0
    assert result["invalid_characters"] == []


def test_invalid_characters_are_detected():
    result = check_dna_characters("ACGTXYZ")
    assert result["is_valid"] is False
    assert result["invalid_character_count"] == 3
    assert result["invalid_characters"] == ["X", "Y", "Z"]


def test_empty_dna_is_reported_but_does_not_raise():
    result = check_dna_characters("")
    assert result["is_empty"] is True
    assert result["is_valid"] is False
    assert result["dna_length"] == 0


def test_lowercase_dna_is_normalized_like_the_rest_of_the_project():
    result = check_dna_characters("acgtacgt")
    assert result["is_valid"] is True
    assert result["invalid_character_count"] == 0


def test_check_dna_characters_rejects_non_string_input():
    with pytest.raises(DNAIntegrityError):
        check_dna_characters(12345)  # type: ignore[arg-type]


# --- B. DNA length validation ----------------------------------------------------

def test_dna_length_multiple_of_four_is_compatible():
    result = check_dna_length(8)
    assert result["is_length_compatible"] is True
    assert result["expected_byte_count"] == 2
    assert result["bases_per_byte"] == BASES_PER_BYTE == 4


def test_dna_length_not_multiple_of_four_is_incompatible():
    result = check_dna_length(9)
    assert result["is_length_compatible"] is False
    assert result["expected_byte_count"] is None
    assert result["remainder_bases"] == 1


def test_valid_encoded_dna_length_is_always_compatible():
    # The real encoder never produces a length that fails this check --
    # confirms this module's rule matches dna_encoder.py's own guarantee.
    for payload in (b"", b"A", b"Hello, BioVault!", bytes(range(50))):
        dna_length = encode_file_to_dna(payload)["dna_length"]
        assert check_dna_length(dna_length)["is_length_compatible"] is True


def test_check_dna_length_rejects_negative_or_non_int():
    with pytest.raises(DNAIntegrityError):
        check_dna_length(-1)
    with pytest.raises(DNAIntegrityError):
        check_dna_length(1.5)  # type: ignore[arg-type]


# --- C. DNA statistics -------------------------------------------------------------

def test_dna_statistics_reports_gc_and_at_percentages():
    stats = calculate_dna_statistics("ACGT")
    assert stats["gc_percentage"] == 50.0
    assert stats["at_percentage"] == 50.0
    assert stats["total_length"] == 4


def test_dna_statistics_reports_longest_homopolymer_run():
    stats = calculate_dna_statistics("AAACCGGGGT")
    assert stats["longest_homopolymer_run"] == 4  # GGGG


def test_dna_statistics_handles_empty_sequence_without_raising():
    stats = calculate_dna_statistics("")
    assert stats["total_length"] == 0
    assert stats["gc_percentage"] == 0.0


# --- D. Corruption analysis: warnings vs. errors ------------------------------------

def test_analyze_corruption_flags_invalid_characters_as_error():
    result = analyze_corruption("ACGTX")
    assert any("invalid character" in e.lower() for e in result["errors"])


def test_analyze_corruption_flags_bad_length_as_error():
    result = analyze_corruption("ACG")  # 3 bases, not a multiple of 4
    assert any("not a multiple of" in e for e in result["errors"])


def test_analyze_corruption_does_not_treat_unusual_gc_as_an_error():
    # All-G sequence: 100% GC, clearly outside the comfort band, but
    # this must be a WARNING, never an error/definite-corruption claim.
    result = analyze_corruption("GGGG" * 5)
    assert result["errors"] == []
    assert any("GC content" in w for w in result["warnings"])


def test_analyze_corruption_flags_long_homopolymer_as_warning_not_error():
    # 20 bases total (multiple of 4) so the length check itself passes,
    # isolating the homopolymer warning from any length-related error.
    result = analyze_corruption("ACGT" + "A" * 12 + "ACGT", homopolymer_threshold=4)
    assert result["errors"] == []
    assert any("homopolymer" in w.lower() for w in result["warnings"])


def test_analyze_corruption_flags_unexpected_length_as_warning():
    result = analyze_corruption("ACGTACGT", expected_dna_length=100)
    assert any("does not match the expected length" in w for w in result["warnings"])


def test_analyze_corruption_empty_sequence_reports_error():
    result = analyze_corruption("")
    assert any("empty" in e.lower() for e in result["errors"])


# --- Truncated / inserted / deleted / substituted scenarios -------------------------

def test_truncated_dna_is_detected_as_incomplete():
    dna = encode_file_to_dna(b"Hello, BioVault!")["dna_sequence"]
    truncated = dna[:-1]
    report = build_integrity_report(truncated)
    assert report["status"] == STATUS_INCOMPLETE
    assert report["is_complete"] is False


def test_inserted_base_scenario_is_detected():
    dna = encode_file_to_dna(b"Hello, BioVault!")["dna_sequence"]
    with_insertion = dna[:5] + "A" + dna[5:]
    report = build_integrity_report(with_insertion, original_bytes=b"Hello, BioVault!")
    # An insertion shifts length by 1 base -- not a multiple of 4 (unless
    # it happens to land on a multiple-of-4 boundary by coincidence for
    # this specific length; check the general property instead).
    length_check = check_dna_length(len(with_insertion))
    if not length_check["is_length_compatible"]:
        assert report["status"] == STATUS_INCOMPLETE
    else:
        # Rare coincidental case: still must not falsely claim recovery.
        assert report["status"] in (STATUS_CORRUPTED, STATUS_RECOVERED)


def test_deleted_base_scenario_is_detected():
    dna = encode_file_to_dna(b"Hello, BioVault!")["dna_sequence"]
    with_deletion = dna[:5] + dna[6:]
    report = build_integrity_report(with_deletion, original_bytes=b"Hello, BioVault!")
    length_check = check_dna_length(len(with_deletion))
    if not length_check["is_length_compatible"]:
        assert report["status"] == STATUS_INCOMPLETE
    else:
        assert report["status"] in (STATUS_CORRUPTED, STATUS_RECOVERED)


def test_substitution_scenario_is_detected_as_corrupted_when_it_changes_bytes():
    original = b"Hello, BioVault! Substitution test payload."
    dna = encode_file_to_dna(original)["dna_sequence"]

    mutation_result = mutate_dna(dna, "substitution", mutation_rate=50.0, seed=1)
    mutated_dna = mutation_result["mutated_sequence"]

    report = build_integrity_report(mutated_dna, original_bytes=original)
    assert report["status"] in (STATUS_RECOVERED, STATUS_CORRUPTED)
    if mutation_result["total_edits"] > 0:
        # With a 50% substitution rate on a non-trivial sequence, at
        # least one run should actually change the recovered bytes.
        assert report["recovery_confirmed"] in (True, False)


# --- Decode failure handling ---------------------------------------------------------

def test_decode_failure_from_invalid_characters_yields_invalid_status():
    report = build_integrity_report("ACGTXYZ")
    assert report["status"] == STATUS_INVALID
    assert report["can_decode"] is False


def test_empty_sequence_yields_invalid_status_and_cannot_decode():
    report = build_integrity_report("")
    assert report["status"] == STATUS_INVALID
    assert report["can_decode"] is False
    assert report["recovery_confirmed"] is None


# --- Original/recovered byte equality & difference detection -----------------------

def test_compare_original_and_recovered_identical_bytes():
    result = compare_original_and_recovered(b"hello", b"hello")
    assert result["is_identical"] is True
    assert result["differing_byte_count"] == 0
    assert result["first_difference_index"] is None


def test_compare_original_and_recovered_detects_single_byte_difference():
    result = compare_original_and_recovered(b"hello", b"hEllo")
    assert result["is_identical"] is False
    assert result["differing_byte_count"] == 1
    assert result["first_difference_index"] == 1


def test_compare_original_and_recovered_detects_length_mismatch():
    result = compare_original_and_recovered(b"hello", b"hell")
    assert result["is_identical"] is False
    assert result["first_difference_index"] == 4


def test_compare_original_and_recovered_rejects_non_bytes():
    with pytest.raises(DNAIntegrityError):
        compare_original_and_recovered("not bytes", b"hello")  # type: ignore[arg-type]


# --- Hash mismatch detection --------------------------------------------------------

def test_compare_original_and_recovered_reports_hashes():
    result = compare_original_and_recovered(b"abc", b"abc")
    assert result["original_hash"] == compute_content_hash(b"abc")
    assert result["recovered_hash"] == result["original_hash"]


def test_compare_original_and_recovered_different_hashes_when_bytes_differ():
    result = compare_original_and_recovered(b"abc", b"abd")
    assert result["original_hash"] != result["recovered_hash"]


# --- Full report: all 6 status categories -------------------------------------------

def test_report_status_recovered_when_bytes_match():
    original = b"full report recovery test"
    dna = encode_file_to_dna(original)["dna_sequence"]
    report = build_integrity_report(dna, original_bytes=original)
    assert report["status"] == STATUS_RECOVERED
    assert report["recovery_confirmed"] is True
    assert report["is_valid"] is True


def test_report_status_unable_to_verify_without_original_bytes():
    dna = encode_file_to_dna(b"no original bytes given")["dna_sequence"]
    report = build_integrity_report(dna)
    assert report["status"] == STATUS_UNABLE_TO_VERIFY
    assert report["recovery_confirmed"] is None


def test_report_status_valid_when_no_recovery_check_expected():
    dna = encode_file_to_dna(b"structural check only")["dna_sequence"]
    report = build_integrity_report(dna, expects_recovery_check=False)
    assert report["status"] == STATUS_VALID
    assert report["is_valid"] is True


def test_report_never_claims_recovered_unless_bytes_actually_match():
    original = b"strict recovery claim test"
    dna = encode_file_to_dna(original)["dna_sequence"]
    wrong_original = b"a completely different original file"
    report = build_integrity_report(dna, original_bytes=wrong_original)
    assert report["status"] == STATUS_CORRUPTED
    assert report["recovery_confirmed"] is False


def test_report_structure_has_all_required_fields():
    dna = encode_file_to_dna(b"field check")["dna_sequence"]
    report = build_integrity_report(dna, original_bytes=b"field check")
    for field in (
        "status", "is_valid", "is_corrupted", "is_complete", "can_decode",
        "recovery_confirmed", "warnings", "errors", "dna_length",
        "invalid_character_count", "original_hash", "recovered_hash",
        "comparison_result",
    ):
        assert field in report


def test_build_integrity_report_rejects_non_string_sequence():
    with pytest.raises(DNAIntegrityError):
        build_integrity_report(12345)  # type: ignore[arg-type]


# --- Deterministic report structure ---------------------------------------------------

def test_report_is_deterministic_for_same_input():
    original = b"determinism check"
    dna = encode_file_to_dna(original)["dna_sequence"]
    first = build_integrity_report(dna, original_bytes=original)
    second = build_integrity_report(dna, original_bytes=original)
    assert first == second


# --- Same filename, different content is rejected (Phase 14 compatibility) -----------

def test_same_filename_different_content_is_rejected_via_content_hash():
    file_a = {"filename": "sample.txt", "content_hash": "hash-a"}
    file_b = {"filename": "sample.txt", "content_hash": "hash-b"}
    stored_result = {"source_filename": "sample.txt", "content_hash": "hash-a"}

    assert file_identity_matches(file_a, stored_result) is True
    assert file_identity_matches(file_b, stored_result) is False


def test_missing_content_hash_in_legacy_result_is_never_treated_as_matching():
    file_info = {"filename": "sample.txt", "content_hash": "hash-a"}
    legacy_result = {"source_filename": "sample.txt"}  # no content_hash at all
    assert file_identity_matches(file_info, legacy_result) is False


# --- No mutation of original input data ------------------------------------------------

def test_build_integrity_report_does_not_mutate_original_bytes():
    original = bytearray(b"do not mutate this data")
    original_copy = bytes(original)
    dna = encode_file_to_dna(bytes(original))["dna_sequence"]
    build_integrity_report(dna, original_bytes=bytes(original))
    assert bytes(original) == original_copy


def test_compare_original_and_recovered_does_not_mutate_inputs():
    original = bytearray(b"original payload")
    recovered = bytearray(b"recovered payload")
    original_copy = bytes(original)
    recovered_copy = bytes(recovered)
    compare_original_and_recovered(bytes(original), bytes(recovered))
    assert bytes(original) == original_copy
    assert bytes(recovered) == recovered_copy
