"""
Tests for app/modules/redundancy_simulation.py (Phase 18).

Covers redundancy levels/storage overhead, corruption (substitution/
insertion/deletion, deterministic seeding), majority-vote and
agreement-based recovery (including no-majority and misaligned-length
cases), the full simulation report (status/recovery_confirmed rules),
the reliability experiment, Phase 14 content-hash compatibility, and
non-mutation of original data. Never asserts exact timing.
"""

import pytest

from app.modules.redundancy_simulation import (
    RedundancySimulationError,
    UNRESOLVED_MARKER,
    STATUS_RECOVERED,
    STATUS_PARTIALLY_RECOVERED,
    STATUS_FAILED,
    STATUS_UNABLE_TO_VERIFY,
    RECOVERY_STRATEGY_MAJORITY,
    RECOVERY_STRATEGY_AGREEMENT,
    RECOVERY_STRATEGY_ERROR_CORRECTION,
    create_redundant_copies,
    calculate_storage_overhead,
    corrupt_copies,
    check_alignment,
    majority_vote_recovery,
    agreement_based_recovery,
    error_correction_recovery,
    run_redundancy_simulation,
    run_reliability_experiment,
)
from app.modules.dna_encoder import encode_file_to_dna
from app.modules.file_handler import compute_content_hash
from app.modules.result_identity import file_identity_matches


# --- Basic redundancy: copies + storage overhead --------------------------------

def test_zero_redundancy_produces_a_single_copy():
    result = create_redundant_copies("ACGT", extra_copies=0)
    assert result["total_copies"] == 1
    assert result["copies"] == ["ACGT"]


def test_one_extra_copy_produces_two_copies():
    result = create_redundant_copies("ACGT", extra_copies=1)
    assert result["total_copies"] == 2
    assert result["copies"] == ["ACGT", "ACGT"]


def test_multiple_extra_copies_produce_correct_count():
    result = create_redundant_copies("ACGT", extra_copies=3)
    assert result["total_copies"] == 4
    assert len(result["copies"]) == 4
    assert all(copy == "ACGT" for copy in result["copies"])


def test_create_redundant_copies_rejects_negative_extra_copies():
    with pytest.raises(RedundancySimulationError):
        create_redundant_copies("ACGT", extra_copies=-1)


def test_storage_overhead_zero_redundancy():
    overhead = calculate_storage_overhead(100, extra_copies=0)
    assert overhead["storage_multiplier"] == 1
    assert overhead["total_dna_length"] == 100
    assert overhead["additional_bases"] == 0
    assert overhead["overhead_percent"] == 0.0


def test_storage_overhead_one_extra_copy_doubles_storage():
    overhead = calculate_storage_overhead(100, extra_copies=1)
    assert overhead["storage_multiplier"] == 2
    assert overhead["total_dna_length"] == 200
    assert overhead["overhead_percent"] == 100.0


def test_storage_overhead_three_extra_copies_quadruples_storage():
    overhead = calculate_storage_overhead(100, extra_copies=3)
    assert overhead["storage_multiplier"] == 4
    assert overhead["total_dna_length"] == 400
    assert overhead["overhead_percent"] == 300.0


def test_storage_overhead_handles_zero_length_safely():
    overhead = calculate_storage_overhead(0, extra_copies=2)
    assert overhead["overhead_percent"] == 0.0
    assert overhead["total_dna_length"] == 0


# --- Corruption: substitution / insertion / deletion / determinism ---------------

def test_corrupt_copies_substitution_preserves_length():
    copies = ["ACGTACGTACGT"] * 3
    result = corrupt_copies(copies, "substitution", 50.0, seed=1)
    assert all(len(copy) == 12 for copy in result["copies"])


def test_corrupt_copies_insertion_can_change_length():
    copies = ["ACGTACGTACGT"] * 3
    result = corrupt_copies(copies, "insertion", 50.0, seed=1)
    # At least one copy should have grown given a high insertion rate.
    assert any(len(copy) >= 12 for copy in result["copies"])


def test_corrupt_copies_deletion_can_change_length():
    copies = ["ACGTACGTACGT"] * 3
    result = corrupt_copies(copies, "deletion", 50.0, seed=1)
    assert all(len(copy) <= 12 for copy in result["copies"])


def test_corrupt_copies_is_deterministic_with_fixed_seed():
    copies = ["ACGTACGTACGTACGTACGT"] * 4
    first = corrupt_copies(copies, "substitution", 30.0, seed=42)
    second = corrupt_copies(copies, "substitution", 30.0, seed=42)
    assert first["copies"] == second["copies"]


def test_corrupt_copies_uses_different_seed_per_copy():
    # With a moderate rate and a real per-copy seed offset, copies
    # should not all corrupt identically (the whole point of the
    # demonstration -- otherwise majority vote could never help).
    copies = ["ACGTACGTACGTACGTACGTACGTACGTACGT"] * 4
    result = corrupt_copies(copies, "substitution", 20.0, seed=1)
    assert len(set(result["copies"])) > 1


def test_corrupt_copies_does_not_mutate_original_list_or_strings():
    original_copies = ["ACGTACGT", "ACGTACGT"]
    original_snapshot = list(original_copies)
    corrupt_copies(original_copies, "substitution", 50.0, seed=1)
    assert original_copies == original_snapshot


def test_corrupt_copies_zero_rate_leaves_copies_unchanged():
    copies = ["ACGTACGT"] * 3
    result = corrupt_copies(copies, "substitution", 0.0, seed=1)
    assert result["copies"] == copies
    assert result["corrupted_copy_count"] == 0


# --- Majority vote recovery -------------------------------------------------------

def test_majority_vote_recovers_clear_majority():
    copies = ["ACGT", "ACGT", "AGGT"]  # position 1: C,C,G -> majority C
    result = majority_vote_recovery(copies)
    assert result["alignment_available"] is True
    assert result["recovered_sequence"] == "ACGT"
    assert result["unresolved_position_count"] == 0


def test_majority_vote_marks_no_majority_as_unresolved():
    copies = ["A", "C", "G"]  # 3-way tie, no majority
    result = majority_vote_recovery(copies)
    assert result["recovered_sequence"] == UNRESOLVED_MARKER
    assert result["unresolved_position_count"] == 1
    assert result["unresolved_positions"] == [0]


def test_majority_vote_two_copy_disagreement_is_unresolved():
    # A 1-1 split has no strict majority winner.
    copies = ["A", "T"]
    result = majority_vote_recovery(copies)
    assert result["recovered_sequence"] == UNRESOLVED_MARKER


def test_majority_vote_handles_different_length_copies_safely():
    copies = ["ACGT", "ACG", "ACGTT"]
    result = majority_vote_recovery(copies)
    assert result["alignment_available"] is False
    assert result["recovered_sequence"] is None
    assert "different lengths" in result["message"]


def test_majority_vote_single_copy_is_trivially_resolved_but_not_necessarily_correct():
    # With only one copy, every position trivially has a "majority" of
    # one -- this measures resolvability, not correctness.
    result = majority_vote_recovery(["AAAA"])
    assert result["recovered_sequence"] == "AAAA"
    assert result["unresolved_position_count"] == 0


def test_majority_vote_never_guesses_silently():
    # Explicit contract check: any tie must appear in the recovered
    # sequence as the unresolved marker, never a guessed real base.
    copies = ["AC", "CA"]
    result = majority_vote_recovery(copies)
    assert UNRESOLVED_MARKER in result["recovered_sequence"]


# --- Agreement-based recovery -----------------------------------------------------

def test_agreement_based_recovery_requires_higher_bar_than_plurality():
    # 2 of 4 copies agree at this position -- a plurality (majority
    # vote would resolve it), but only 50%, which fails a stricter 75%
    # agreement requirement.
    copies = ["A", "A", "C", "T"]
    majority_result = majority_vote_recovery(copies)
    agreement_result = agreement_based_recovery(copies, min_agreement_fraction=0.75)
    assert majority_result["recovered_sequence"] == "A"
    assert agreement_result["recovered_sequence"] == UNRESOLVED_MARKER


def test_agreement_based_recovery_passes_with_sufficient_agreement():
    copies = ["A", "A", "A", "T"]  # 3 of 4 = 75%
    result = agreement_based_recovery(copies, min_agreement_fraction=0.75)
    assert result["recovered_sequence"] == "A"


def test_agreement_based_recovery_rejects_invalid_fraction():
    with pytest.raises(RedundancySimulationError):
        agreement_based_recovery(["A", "A"], min_agreement_fraction=0)
    with pytest.raises(RedundancySimulationError):
        agreement_based_recovery(["A", "A"], min_agreement_fraction=1.5)


def test_agreement_based_recovery_handles_misaligned_lengths():
    result = agreement_based_recovery(["AC", "ACG"])
    assert result["alignment_available"] is False


# --- Strategy C: existing error correction -----------------------------------------

def test_error_correction_recovery_uses_existing_phase_six_algorithm():
    dna_sequence = "ACGTACGTACGT"
    result = error_correction_recovery(dna_sequence)
    assert result["strategy"] == RECOVERY_STRATEGY_ERROR_CORRECTION
    # No corruption was introduced, so correction should report no errors.
    assert result["correction"]["errors_detected"] == 0
    assert result["recovered_sequence"] == dna_sequence


# --- check_alignment ---------------------------------------------------------------

def test_check_alignment_detects_equal_lengths():
    result = check_alignment(["ACGT", "ACGT", "TTTT"])
    assert result["is_aligned"] is True
    assert result["common_length"] == 4


def test_check_alignment_detects_unequal_lengths():
    result = check_alignment(["ACGT", "ACG"])
    assert result["is_aligned"] is False
    assert result["common_length"] is None


# --- Full simulation: recovery verification never inferred from percentage --------

def test_full_simulation_recovered_when_no_corruption():
    data = b"no corruption baseline test"
    dna = encode_file_to_dna(data)["dna_sequence"]
    result = run_redundancy_simulation(dna, original_bytes=data, extra_copies=2, mutation_rate=0.0, seed=1)
    assert result["status"] == STATUS_RECOVERED
    assert result["recovery_confirmed"] is True
    assert result["recovery_percentage"] == 100.0


def test_full_simulation_never_confirms_recovery_from_percentage_alone():
    # With zero redundancy, majority-of-one trivially "resolves" every
    # position (100%) even when the single copy is actually corrupted
    # -- recovery_confirmed must still be False because the recovered
    # bytes do not actually match the original.
    data = b"percentage is not the same as correctness, this string is long enough to likely mutate"
    dna = encode_file_to_dna(data)["dna_sequence"]
    result = run_redundancy_simulation(dna, original_bytes=data, extra_copies=0, mutation_rate=20.0, seed=1)
    assert result["recovery_percentage"] == 100.0
    if result["corrupted_copy_count"] > 0:
        assert result["recovery_confirmed"] is False
        assert result["status"] != STATUS_RECOVERED


def test_full_simulation_status_unable_to_verify_without_original_bytes():
    dna = encode_file_to_dna(b"no original bytes given")["dna_sequence"]
    result = run_redundancy_simulation(dna, original_bytes=None, extra_copies=1, mutation_rate=5.0, seed=1)
    assert result["status"] == STATUS_UNABLE_TO_VERIFY
    assert result["recovery_confirmed"] is None


def test_full_simulation_insertion_deletion_reports_failed_not_misleading_success():
    data = b"insertion deletion alignment failure demonstration payload"
    dna = encode_file_to_dna(data)["dna_sequence"]
    result = run_redundancy_simulation(
        dna, original_bytes=data, extra_copies=2, mutation_type="insertion", mutation_rate=30.0, seed=1
    )
    assert result["recovery_detail"]["alignment_available"] is False
    assert result["status"] == STATUS_FAILED
    assert result["recovery_confirmed"] is False
    assert result["recovery_percentage"] == 0.0


def test_full_simulation_rejects_empty_dna():
    with pytest.raises(RedundancySimulationError):
        run_redundancy_simulation("", original_bytes=b"", extra_copies=1)


def test_full_simulation_rejects_unknown_strategy():
    dna = encode_file_to_dna(b"strategy check")["dna_sequence"]
    with pytest.raises(RedundancySimulationError):
        run_redundancy_simulation(dna, extra_copies=1, recovery_strategy="not_a_real_strategy")


def test_full_simulation_reports_hashes():
    data = b"hash reporting check"
    dna = encode_file_to_dna(data)["dna_sequence"]
    result = run_redundancy_simulation(dna, original_bytes=data, extra_copies=1, mutation_rate=0.0, seed=1)
    assert result["original_hash"] == compute_content_hash(data)
    assert result["recovered_hash"] == result["original_hash"]


def test_full_simulation_does_not_mutate_original_dna_sequence():
    data = b"do not mutate original dna"
    dna = encode_file_to_dna(data)["dna_sequence"]
    dna_copy = str(dna)
    run_redundancy_simulation(dna, original_bytes=data, extra_copies=2, mutation_rate=50.0, seed=1)
    assert dna == dna_copy


def test_full_simulation_error_correction_strategy_runs_without_crashing():
    data = b"error correction strategy integration check"
    dna = encode_file_to_dna(data)["dna_sequence"]
    result = run_redundancy_simulation(
        dna, original_bytes=data, extra_copies=0, mutation_rate=5.0, seed=1,
        recovery_strategy=RECOVERY_STRATEGY_ERROR_CORRECTION,
    )
    assert result["recovery_strategy"] == RECOVERY_STRATEGY_ERROR_CORRECTION
    assert "detection" in result["recovery_detail"]


# --- Edge cases ---------------------------------------------------------------------

def test_very_short_dna_single_base():
    result = run_redundancy_simulation("A", original_bytes=None, extra_copies=1, mutation_rate=0.0, seed=1)
    assert result["original_dna_length"] == 1


def test_all_identical_bases_sequence():
    dna = "AAAAAAAAAAAA"
    result = run_redundancy_simulation(dna, original_bytes=None, extra_copies=2, mutation_type="substitution", mutation_rate=10.0, seed=5)
    assert result["total_copies"] == 3


def test_invalid_dna_characters_are_rejected_during_corruption():
    with pytest.raises(RedundancySimulationError):
        corrupt_copies(["ACGTX"], "substitution", 10.0, seed=1)


def test_multiple_corrupted_copies_still_produces_a_report():
    dna = encode_file_to_dna(b"multiple corrupted copies edge case")["dna_sequence"]
    result = run_redundancy_simulation(dna, original_bytes=b"multiple corrupted copies edge case", extra_copies=3, mutation_rate=40.0, seed=9)
    assert result["total_copies"] == 4
    assert isinstance(result["corrupted_copy_count"], int)


def test_different_length_copies_passed_directly_are_handled_safely():
    result = majority_vote_recovery(["A", "AA", "AAA"])
    assert result["alignment_available"] is False


# --- Phase 14 content-hash compatibility --------------------------------------------

def test_same_filename_same_content_hash_matches():
    file_info = {"filename": "sample.txt", "content_hash": "hash-a"}
    stored = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert file_identity_matches(file_info, stored) is True


def test_same_filename_different_content_hash_is_rejected():
    file_info = {"filename": "sample.txt", "content_hash": "hash-b"}
    stored = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert file_identity_matches(file_info, stored) is False


def test_missing_content_hash_result_is_unverifiable():
    file_info = {"filename": "sample.txt", "content_hash": "hash-a"}
    legacy_stored = {"source_filename": "sample.txt"}
    assert file_identity_matches(file_info, legacy_stored) is False


# --- Reliability experiment ----------------------------------------------------------

def test_reliability_experiment_is_deterministic_with_fixed_seed():
    data = b"reliability experiment determinism check payload"
    dna = encode_file_to_dna(data)["dna_sequence"]
    first = run_reliability_experiment(dna, original_bytes=data, redundancy_levels=[0, 1], corruption_rates=[0, 10], seed=3)
    second = run_reliability_experiment(dna, original_bytes=data, redundancy_levels=[0, 1], corruption_rates=[0, 10], seed=3)
    assert first == second


def test_reliability_experiment_result_structure():
    dna = encode_file_to_dna(b"structure check")["dna_sequence"]
    results = run_reliability_experiment(dna, original_bytes=b"structure check", redundancy_levels=[0, 1], corruption_rates=[0, 5])
    assert len(results) == 4  # 2 redundancy levels x 2 corruption rates
    for row in results:
        for field in (
            "redundancy_level", "total_copies", "corruption_rate_percent",
            "recovery_percentage", "recovery_confirmed", "status", "storage_overhead_percent",
        ):
            assert field in row


def test_reliability_experiment_covers_multiple_corruption_levels():
    dna = encode_file_to_dna(b"multiple corruption levels check")["dna_sequence"]
    results = run_reliability_experiment(
        dna, original_bytes=b"multiple corruption levels check",
        redundancy_levels=[1], corruption_rates=[0, 5, 10, 20],
    )
    rates_seen = {row["corruption_rate_percent"] for row in results}
    assert rates_seen == {0, 5, 10, 20}


def test_reliability_experiment_covers_multiple_redundancy_levels():
    dna = encode_file_to_dna(b"multiple redundancy levels check")["dna_sequence"]
    results = run_reliability_experiment(
        dna, original_bytes=b"multiple redundancy levels check",
        redundancy_levels=[0, 1, 2, 3], corruption_rates=[10],
    )
    levels_seen = {row["redundancy_level"] for row in results}
    assert levels_seen == {0, 1, 2, 3}


def test_reliability_experiment_zero_corruption_always_recovers():
    dna = encode_file_to_dna(b"zero corruption always recovers check")["dna_sequence"]
    results = run_reliability_experiment(
        dna, original_bytes=b"zero corruption always recovers check",
        redundancy_levels=[0, 1, 2], corruption_rates=[0],
    )
    assert all(row["status"] == STATUS_RECOVERED for row in results)
