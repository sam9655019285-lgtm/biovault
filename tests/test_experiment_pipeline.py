"""
Tests for app/modules/experiment_pipeline.py (Phase 20).

Covers the full orchestrated experiment: encoding, DNA analysis,
storage/capacity analysis, redundancy, corruption, recovery, integrity,
performance, and the final honest overall-status derivation. Verifies
reuse of existing modules (no duplicated logic), Phase 14 content-hash
compatibility, and non-mutation of input data. Never asserts exact
timing values.
"""

import pytest

from app.modules.experiment_pipeline import (
    ExperimentPipelineError,
    EXPERIMENT_STATUS_RECOVERED,
    EXPERIMENT_STATUS_FAILED,
    EXPERIMENT_STATUS_UNABLE_TO_VERIFY,
    EXPERIMENT_STATUS_NOT_AVAILABLE,
    STAGE_NAMES,
    run_experiment,
    generate_experiment_report_text,
)
from app.modules.dna_encoder import encode_file_to_dna
from app.modules.file_handler import compute_content_hash
from app.modules.result_identity import file_identity_matches
from app.modules.redundancy_simulation import RECOVERY_STRATEGY_MAJORITY, RECOVERY_STRATEGY_ERROR_CORRECTION


PAYLOAD = b"BioVault Phase 20 experiment pipeline test payload, long enough to be meaningful for statistics."


# --- Basic structure / reuse ---------------------------------------------------------

def test_run_experiment_returns_all_required_top_level_sections():
    result = run_experiment(PAYLOAD, "sample.txt", extra_copies=1, mutation_rate=0.0, seed=1)
    for key in (
        "experiment_id", "source_filename", "content_hash", "file_size_bytes",
        "encoding", "dna_analysis", "storage_analysis", "capacity_analysis",
        "redundancy", "corruption", "recovery", "integrity", "performance",
        "overall_status", "stage_names",
    ):
        assert key in result


def test_run_experiment_uses_the_real_encoder_output():
    result = run_experiment(PAYLOAD, "sample.txt", mutation_rate=0.0, seed=1)
    real_encoding = encode_file_to_dna(PAYLOAD)
    assert result["encoding"]["dna_length"] == real_encoding["dna_length"]


def test_experiment_id_is_unique_per_run():
    first = run_experiment(PAYLOAD, "sample.txt", mutation_rate=0.0, seed=1)
    second = run_experiment(PAYLOAD, "sample.txt", mutation_rate=0.0, seed=1)
    assert first["experiment_id"] != second["experiment_id"]


def test_content_hash_matches_file_handler():
    result = run_experiment(PAYLOAD, "sample.txt", mutation_rate=0.0, seed=1)
    assert result["content_hash"] == compute_content_hash(PAYLOAD)


def test_stage_names_are_reported():
    result = run_experiment(PAYLOAD, "sample.txt", mutation_rate=0.0, seed=1)
    assert result["stage_names"] == STAGE_NAMES
    assert len(STAGE_NAMES) == 11


# --- Overall status: never claims success without proof --------------------------

def test_zero_corruption_yields_successfully_recovered():
    result = run_experiment(PAYLOAD, "sample.txt", extra_copies=1, mutation_rate=0.0, seed=1)
    assert result["overall_status"] == EXPERIMENT_STATUS_RECOVERED
    assert result["recovery"]["recovery_confirmed"] is True


def test_high_corruption_with_no_redundancy_does_not_falsely_claim_success():
    result = run_experiment(
        b"percentage should never be confused with actual correctness in this experiment pipeline test",
        "sample.txt", extra_copies=0, mutation_type="substitution", mutation_rate=25.0, seed=1,
    )
    if result["corruption"]["corrupted_copy_count"]:
        assert result["overall_status"] != EXPERIMENT_STATUS_RECOVERED
        assert result["recovery"]["recovery_confirmed"] is False


def test_insertion_deletion_alignment_failure_reports_not_available_status():
    result = run_experiment(
        PAYLOAD, "sample.txt", extra_copies=2, mutation_type="insertion", mutation_rate=30.0, seed=1,
    )
    assert result["overall_status"] == EXPERIMENT_STATUS_NOT_AVAILABLE


def test_empty_file_reports_unable_to_verify():
    result = run_experiment(b"", "empty.txt", extra_copies=1)
    assert result["overall_status"] == EXPERIMENT_STATUS_UNABLE_TO_VERIFY
    assert result["dna_analysis"] is None
    assert result["encoding"]["dna_length"] == 0


def test_error_correction_strategy_runs_end_to_end():
    result = run_experiment(
        PAYLOAD, "sample.txt", extra_copies=0, mutation_type="substitution", mutation_rate=5.0, seed=2,
        recovery_strategy=RECOVERY_STRATEGY_ERROR_CORRECTION,
    )
    assert result["recovery"]["strategy"] == RECOVERY_STRATEGY_ERROR_CORRECTION
    assert result["overall_status"] in (
        EXPERIMENT_STATUS_RECOVERED, EXPERIMENT_STATUS_FAILED,
        EXPERIMENT_STATUS_NOT_AVAILABLE, EXPERIMENT_STATUS_UNABLE_TO_VERIFY,
    )


# --- DNA analysis labeled as simulation/educational --------------------------------

def test_dna_analysis_is_labeled_as_simulation_indicator():
    result = run_experiment(PAYLOAD, "sample.txt", mutation_rate=0.0, seed=1)
    assert result["dna_analysis"]["category"] == "simulation_educational_indicator"


def test_dna_analysis_reports_expected_fields():
    result = run_experiment(PAYLOAD, "sample.txt", mutation_rate=0.0, seed=1)
    analysis = result["dna_analysis"]
    assert set(analysis["base_counts"].keys()) == {"A", "C", "G", "T"}
    assert 0 <= analysis["gc_percentage"] <= 100
    assert analysis["longest_homopolymer_run"] >= 0


# --- Redundancy integration (Phase 18 reused) ---------------------------------------

@pytest.mark.parametrize("extra_copies,expected_multiplier", [(0, 1), (1, 2), (2, 3), (3, 4)])
def test_redundancy_levels_produce_correct_multiplier(extra_copies, expected_multiplier):
    result = run_experiment(PAYLOAD, "sample.txt", extra_copies=extra_copies, mutation_rate=0.0, seed=1)
    assert result["redundancy"]["total_copies"] == expected_multiplier
    dna_length = result["encoding"]["dna_length"]
    assert result["redundancy"]["total_dna_length"] == dna_length * expected_multiplier


# --- Capacity analysis integration (Phase 19 reused) --------------------------------

def test_capacity_analysis_matches_zero_overhead_for_real_encoding():
    result = run_experiment(PAYLOAD, "sample.txt", mutation_rate=0.0, seed=1)
    assert result["capacity_analysis"]["category"] == "measured_vs_theoretical"
    assert result["encoding"]["theoretical_dna_length"] == result["encoding"]["dna_length"]
    assert result["encoding"]["encoding_overhead_percent"] == 0.0
    assert result["encoding"]["effective_bits_per_base"] == 2.0


# --- Integrity verification (Phase 17 reused) ---------------------------------------

def test_baseline_integrity_status_is_present():
    result = run_experiment(PAYLOAD, "sample.txt", mutation_rate=0.0, seed=1)
    assert result["integrity"]["baseline_status"] == "recovered"


def test_integrity_hashes_match_only_when_actually_identical():
    result = run_experiment(PAYLOAD, "sample.txt", extra_copies=1, mutation_rate=0.0, seed=1)
    assert result["integrity"]["original_hash"] == result["integrity"]["recovered_hash"]
    assert result["integrity"]["hashes_match"] is True
    assert result["integrity"]["exact_byte_recovery"] is True


# --- Performance measurement (Phase 15 reused) --------------------------------------

def test_performance_measurements_are_non_negative_and_labeled():
    result = run_experiment(PAYLOAD, "sample.txt", mutation_rate=0.0, seed=1)
    performance = result["performance"]
    assert performance["encoding_time_seconds"] >= 0
    assert performance["encoding_peak_memory_bytes"] >= 0
    assert performance["decoding_time_seconds"] >= 0
    assert performance["note"] == "Measured on this computer"


# --- Report generation ---------------------------------------------------------------

def test_generate_experiment_report_text_contains_real_values():
    result = run_experiment(PAYLOAD, "report_test.txt", extra_copies=1, mutation_rate=0.0, seed=1)
    report_text = generate_experiment_report_text(result)
    assert "report_test.txt" in report_text
    assert result["experiment_id"] in report_text
    assert str(result["encoding"]["dna_length"]) in report_text
    assert result["overall_status"] in report_text
    assert "educational simulation" in report_text.lower() or "SOFTWARE SIMULATION" in report_text


def test_report_never_claims_laboratory_validation():
    result = run_experiment(PAYLOAD, "report_test.txt", mutation_rate=0.0, seed=1)
    report_text = generate_experiment_report_text(result).lower()
    assert "laboratory" in report_text
    assert "does not represent real dna synthesis" in report_text


# --- Input validation / edge cases ----------------------------------------------------

def test_run_experiment_rejects_non_bytes_input():
    with pytest.raises(ExperimentPipelineError):
        run_experiment("not bytes", "sample.txt")  # type: ignore[arg-type]


def test_run_experiment_rejects_empty_filename():
    with pytest.raises(ExperimentPipelineError):
        run_experiment(PAYLOAD, "")


def test_run_experiment_handles_single_byte_input():
    result = run_experiment(b"A", "single_byte.txt", extra_copies=1, mutation_rate=0.0, seed=1)
    assert result["file_size_bytes"] == 1
    assert result["encoding"]["dna_length"] == 4  # 1 byte -> 4 bases, always exact


# --- Phase 14 content-hash compatibility ---------------------------------------------

def test_same_filename_same_hash_matches():
    file_info = {"filename": "sample.txt", "content_hash": compute_content_hash(PAYLOAD)}
    result = run_experiment(PAYLOAD, "sample.txt", mutation_rate=0.0, seed=1)
    stored = {"source_filename": result["source_filename"], "content_hash": result["content_hash"]}
    assert file_identity_matches(file_info, stored) is True


def test_same_filename_different_content_is_rejected():
    result_a = run_experiment(b"content A", "sample.txt", mutation_rate=0.0, seed=1)
    file_info_b = {"filename": "sample.txt", "content_hash": compute_content_hash(b"content B different")}
    stored_a = {"source_filename": result_a["source_filename"], "content_hash": result_a["content_hash"]}
    assert file_identity_matches(file_info_b, stored_a) is False


def test_missing_content_hash_is_unverifiable():
    file_info = {"filename": "sample.txt", "content_hash": "some-hash"}
    legacy_result = {"source_filename": "sample.txt"}  # no content_hash key
    assert file_identity_matches(file_info, legacy_result) is False


# --- Non-mutation of input data ---------------------------------------------------------

def test_run_experiment_does_not_mutate_input_bytes():
    data = bytearray(PAYLOAD)
    original_copy = bytes(data)
    run_experiment(bytes(data), "sample.txt", extra_copies=2, mutation_rate=30.0, seed=5)
    assert bytes(data) == original_copy


def test_run_experiment_does_not_affect_the_real_encoder_module_state():
    before = encode_file_to_dna(PAYLOAD)["dna_sequence"]
    run_experiment(PAYLOAD, "sample.txt", extra_copies=3, mutation_type="deletion", mutation_rate=50.0, seed=9)
    after = encode_file_to_dna(PAYLOAD)["dna_sequence"]
    assert before == after
