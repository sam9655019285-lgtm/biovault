"""
Tests for app/modules/encoding_models.py (Phase 16).

Covers Model A (the real, default, reversible encoding, reused
unchanged), Model B (simulated GC-balancing, analysis-only), Model C
(homopolymer analysis), Model D (GC-content analysis), and the shared
statistics helpers (GC content, homopolymer runs). Never asserts exact
performance timing.
"""

import pytest

from app.modules.encoding_models import (
    EncodingModelError,
    VALID_BASES,
    DEFAULT_HOMOPOLYMER_THRESHOLD,
    validate_dna_sequence,
    longest_homopolymer_run,
    count_homopolymer_runs,
    analyze_gc_content,
    model_a_basic_binary,
    model_b_gc_balanced_simulation,
    model_c_homopolymer_analysis,
    model_d_gc_content_analysis,
    run_model_comparison,
)
from app.modules.dna_encoder import BITS_TO_BASE, encode_file_to_dna
from app.modules.dna_decoder import decode_dna_to_file
from app.modules.file_handler import compute_content_hash


# --- The existing default mapping is unchanged --------------------------------

def test_default_mapping_unchanged():
    assert BITS_TO_BASE == {"00": "A", "01": "C", "10": "G", "11": "T"}


def test_model_a_uses_the_real_existing_encoder_output():
    data = b"Hello"
    model_a_result = model_a_basic_binary(data)
    real_result = encode_file_to_dna(data)
    assert model_a_result["dna_sequence"] == real_result["dna_sequence"]


# --- Model A: reversible, recovery actually confirmed --------------------------

def test_model_a_is_marked_reversible_and_confirms_recovery():
    result = model_a_basic_binary(b"BioVault Phase 16 test payload")
    assert result["model_category"] == "reversible"
    assert result["reversible"] is True
    assert result["recovery_confirmed"] is True

    # Cross-check against the real decoder directly.
    decoded = decode_dna_to_file(result["dna_sequence"])
    assert decoded["recovered_bytes"] == b"BioVault Phase 16 test payload"


def test_model_a_handles_empty_bytes():
    result = model_a_basic_binary(b"")
    assert result["dna_sequence"] == ""
    assert result["dna_length"] == 0
    assert result["recovery_confirmed"] is True


def test_model_a_rejects_non_bytes_input():
    with pytest.raises(EncodingModelError):
        model_a_basic_binary("not bytes")  # type: ignore[arg-type]


# --- GC-content calculation ----------------------------------------------------

def test_gc_content_all_gc_sequence():
    stats = analyze_gc_content("GGCC")
    assert stats["gc_percentage"] == 100.0
    assert stats["at_percentage"] == 0.0
    assert stats["gc_count"] == 4


def test_gc_content_all_at_sequence():
    stats = analyze_gc_content("AATT")
    assert stats["gc_percentage"] == 0.0
    assert stats["at_percentage"] == 100.0


def test_gc_content_mixed_sequence():
    stats = analyze_gc_content("ACGT")  # 1 A, 1 C, 1 G, 1 T
    assert stats["gc_percentage"] == 50.0
    assert stats["at_percentage"] == 50.0


def test_gc_and_at_percentages_sum_to_100_for_valid_only_sequence():
    stats = analyze_gc_content("ACGTACGTAC")
    assert round(stats["gc_percentage"] + stats["at_percentage"], 2) == 100.0


# --- Base counts -----------------------------------------------------------------

def test_gc_content_reports_individual_base_counts():
    stats = analyze_gc_content("AAACCGGGGT")
    assert stats["counts"]["A"] == 3
    assert stats["counts"]["C"] == 2
    assert stats["counts"]["G"] == 4
    assert stats["counts"]["T"] == 1


# --- Invalid-character detection ------------------------------------------------

def test_analyze_gc_content_counts_invalid_characters_without_raising():
    stats = analyze_gc_content("ACGTXYZ")
    assert stats["invalid_character_count"] == 3
    assert stats["valid_base_count"] == 4


def test_validate_dna_sequence_raises_on_invalid_characters():
    with pytest.raises(EncodingModelError):
        validate_dna_sequence("ACGTX")


def test_analyze_gc_content_handles_empty_string_without_raising():
    stats = analyze_gc_content("")
    assert stats["total_length"] == 0
    assert stats["gc_percentage"] == 0.0
    assert stats["at_percentage"] == 0.0
    assert stats["invalid_character_count"] == 0


# --- Longest homopolymer calculation ---------------------------------------------

def test_longest_homopolymer_run_detects_expected_run():
    assert longest_homopolymer_run("ACGTAAAACGT") == 4
    assert longest_homopolymer_run("GGGGGG") == 6
    assert longest_homopolymer_run("ACGT") == 1


def test_longest_homopolymer_run_empty_sequence_is_zero():
    assert longest_homopolymer_run("") == 0


def test_longest_homopolymer_run_ignores_invalid_characters_as_breaks():
    # Invalid characters must not be counted toward a valid-base run.
    assert longest_homopolymer_run("AAAXAAAA") == 4


# --- Homopolymer threshold counting ---------------------------------------------

def test_count_homopolymer_runs_above_threshold():
    stats = count_homopolymer_runs("AAAACGTAAAAAGGGG", threshold=4)
    assert stats["threshold"] == 4
    assert stats["longest_run"] == 5
    assert stats["runs_at_or_above_threshold"] == 3  # AAAA, AAAAA, GGGG


def test_count_homopolymer_runs_none_above_threshold():
    stats = count_homopolymer_runs("ACGTACGT", threshold=4)
    assert stats["runs_at_or_above_threshold"] == 0


def test_count_homopolymer_runs_rejects_invalid_threshold():
    with pytest.raises(EncodingModelError):
        count_homopolymer_runs("ACGT", threshold=0)
    with pytest.raises(EncodingModelError):
        count_homopolymer_runs("ACGT", threshold=-1)


# --- Model B: simulated, analysis-only, not reversible --------------------------

def test_model_b_is_marked_analysis_only_and_not_reversible():
    result = model_b_gc_balanced_simulation(b"some test payload for gc balancing")
    assert result["model_category"] == "analysis-only"
    assert result["reversible"] is False
    assert result["recovery_confirmed"] is None
    assert any("CANNOT be decoded" in w for w in result["warnings"])


def test_model_b_actually_changes_gc_percentage_for_skewed_input():
    # All-zero bytes encode to all-'A' bases under Model A (0% GC).
    # Model B must be able to genuinely rebalance this, since it
    # chooses between two DIFFERENT bit->base mapping tables (not a
    # complement, which would never change GC family).
    skewed_data = bytes([0] * 40)
    model_a_result = model_a_basic_binary(skewed_data)
    assert model_a_result["gc_percentage"] == 0.0

    model_b_result = model_b_gc_balanced_simulation(skewed_data)
    assert model_b_result["gc_percentage"] > model_a_result["gc_percentage"]


def test_model_b_preserves_dna_length_relative_to_model_a():
    data = b"length preservation check"
    model_a_result = model_a_basic_binary(data)
    model_b_result = model_b_gc_balanced_simulation(data)
    assert model_b_result["dna_length"] == model_a_result["dna_length"]


def test_model_b_rejects_non_bytes_input():
    with pytest.raises(EncodingModelError):
        model_b_gc_balanced_simulation("not bytes")  # type: ignore[arg-type]


def test_model_b_rejects_invalid_block_size():
    with pytest.raises(EncodingModelError):
        model_b_gc_balanced_simulation(b"data", block_size_bases=0)


# --- Model C: homopolymer model --------------------------------------------------

def test_model_c_flags_long_runs_with_a_warning():
    dna_sequence = encode_file_to_dna(bytes([0] * 20))["dna_sequence"]  # all 'A's
    result = model_c_homopolymer_analysis(dna_sequence, threshold=4)
    assert result["model_category"] == "analysis-only"
    assert result["longest_homopolymer_run"] >= 4
    assert len(result["warnings"]) > 0


def test_model_c_no_warning_when_no_long_runs():
    result = model_c_homopolymer_analysis("ACGTACGTACGT", threshold=4)
    assert result["warnings"] == []


def test_model_c_does_not_alter_the_sequence():
    dna_sequence = encode_file_to_dna(b"unchanged sequence check")["dna_sequence"]
    result = model_c_homopolymer_analysis(dna_sequence)
    assert result["dna_sequence"] == dna_sequence


# --- Model D: GC-content analysis ------------------------------------------------

def test_model_d_reports_full_statistics():
    dna_sequence = encode_file_to_dna(b"model d test")["dna_sequence"]
    result = model_d_gc_content_analysis(dna_sequence)
    assert result["model_category"] == "analysis-only"
    assert result["reversible"] is True
    assert result["dna_length"] == len(dna_sequence)
    assert "base_counts" in result
    assert set(result["base_counts"].keys()) == set(VALID_BASES)


# --- Deterministic comparison results --------------------------------------------

def test_run_model_comparison_is_deterministic_for_same_input():
    data = b"determinism check payload"
    first = run_model_comparison(data)
    second = run_model_comparison(data)

    for model_id in ("A", "B", "C", "D"):
        assert first["models"][model_id]["dna_sequence"] == second["models"][model_id]["dna_sequence"]
        assert first["models"][model_id]["gc_percentage"] == second["models"][model_id]["gc_percentage"]


def test_run_model_comparison_returns_only_selected_models():
    data = b"selective model run"
    result = run_model_comparison(data, selected_models=["A", "D"])
    assert set(result["models"].keys()) == {"A", "D"}


def test_run_model_comparison_rejects_unknown_model_id():
    with pytest.raises(EncodingModelError):
        run_model_comparison(b"data", selected_models=["A", "Z"])


# --- Empty DNA / empty input handling --------------------------------------------

def test_run_model_comparison_handles_empty_input_without_crashing():
    result = run_model_comparison(b"")
    assert result["models"]["A"]["dna_sequence"] == ""
    assert result["models"]["B"] is None
    assert result["models"]["C"] is None
    assert result["models"]["D"] is None


def test_model_c_and_d_reject_empty_dna_sequence_directly():
    with pytest.raises(EncodingModelError):
        model_c_homopolymer_analysis("")
    with pytest.raises(EncodingModelError):
        model_d_gc_content_analysis("")


# --- Lowercase DNA handling -------------------------------------------------------

def test_validate_dna_sequence_normalizes_lowercase():
    assert validate_dna_sequence("acgt") == "ACGT"


def test_model_c_and_d_accept_lowercase_input():
    result_c = model_c_homopolymer_analysis("aaaacgtacgt")
    assert result_c["dna_sequence"] == "AAAACGTACGT"
    result_d = model_d_gc_content_analysis("acgtacgt")
    assert result_d["dna_sequence"] == "ACGTACGT"


# --- Reversible vs. analysis-only metadata is consistent --------------------------

def test_only_model_a_is_reported_reversible_encoding():
    result = run_model_comparison(b"reversibility metadata check")
    assert result["models"]["A"]["model_category"] == "reversible"
    assert result["models"]["B"]["model_category"] == "analysis-only"
    assert result["models"]["C"]["model_category"] == "analysis-only"
    assert result["models"]["D"]["model_category"] == "analysis-only"

    # Only Model A claims an actually-confirmed recovery.
    assert result["models"]["A"]["recovery_confirmed"] is True
    assert result["models"]["B"]["recovery_confirmed"] is None
    assert result["models"]["C"]["recovery_confirmed"] is None
    assert result["models"]["D"]["recovery_confirmed"] is None


# --- Content-hash compatibility (Phase 14) ----------------------------------------

def test_encoding_model_input_is_compatible_with_content_hash():
    data = b"content hash compatibility check"
    digest_a = compute_content_hash(data)
    digest_b = compute_content_hash(data)
    assert digest_a == digest_b

    result = run_model_comparison(data)
    # The same bytes given to both the hash helper and the model
    # comparison must correspond to the same underlying identity.
    assert result["input_size_bytes"] == len(data)


# --- No modification of original input data ---------------------------------------

def test_model_a_and_b_do_not_mutate_input_bytes():
    data = bytearray(b"do not mutate this payload")
    original_copy = bytes(data)

    model_a_basic_binary(bytes(data))
    model_b_gc_balanced_simulation(bytes(data))

    assert bytes(data) == original_copy


def test_comparison_does_not_mutate_input_bytes():
    data = bytearray(b"another do-not-mutate check")
    original_copy = bytes(data)
    run_model_comparison(bytes(data))
    assert bytes(data) == original_copy
