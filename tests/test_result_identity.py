"""
Tests for app/modules/result_identity.py (Phase 14).

Covers the full staleness-matching matrix every page relies on:
matching/mismatching filename, matching/mismatching content hash,
legacy results with no content_hash, missing DNA-sequence fields, and
missing/empty session-state values -- none of which should ever crash.
"""

import pytest

from app.modules.result_identity import file_identity_matches, result_matches


FILE_A = {"filename": "sample.txt", "content_hash": "hash-a"}
FILE_A_SAME_CONTENT = {"filename": "sample.txt", "content_hash": "hash-a"}
FILE_B_SAME_NAME_DIFFERENT_CONTENT = {"filename": "sample.txt", "content_hash": "hash-b"}
FILE_C_DIFFERENT_NAME_SAME_HASH = {"filename": "other.txt", "content_hash": "hash-a"}


# --- file_identity_matches: filename + hash matrix ----------------------------

def test_matching_filename_and_matching_hash():
    result = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert file_identity_matches(FILE_A, result) is True


def test_matching_filename_but_different_hash():
    # Same filename, different content -- the exact Phase 14 scenario.
    result = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert file_identity_matches(FILE_B_SAME_NAME_DIFFERENT_CONTENT, result) is False


def test_different_filename_but_matching_hash():
    # Identity requires BOTH filename and hash to agree -- a hash
    # collision alone (or a renamed-but-identical file) is not enough.
    result = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert file_identity_matches(FILE_C_DIFFERENT_NAME_SAME_HASH, result) is False


def test_same_filename_identical_content_reuses_matching_result_safely():
    result = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert file_identity_matches(FILE_A_SAME_CONTENT, result) is True


def test_missing_hash_in_legacy_result_never_matches():
    # Legacy result with no content_hash key at all: treated as
    # unverifiable, never matches -- even for the identical file.
    legacy_result = {"source_filename": "sample.txt"}
    assert file_identity_matches(FILE_A, legacy_result) is False


def test_missing_hash_in_legacy_result_never_matches_even_same_filename_different_file():
    # The critical guarantee: a legacy result must never appear valid
    # for a different file that happens to share the same filename.
    legacy_result = {"source_filename": "sample.txt"}
    assert file_identity_matches(FILE_B_SAME_NAME_DIFFERENT_CONTENT, legacy_result) is False


# --- Missing / empty inputs never crash --------------------------------------

def test_none_file_info_returns_false():
    assert file_identity_matches(None, {"source_filename": "a.txt", "content_hash": "h"}) is False


def test_none_result_returns_false():
    assert file_identity_matches(FILE_A, None) is False


def test_empty_dicts_return_false():
    assert file_identity_matches({}, {}) is False


# --- result_matches: identity + optional DNA-sequence field -------------------

def test_result_matches_requires_identity_and_dna_sequence():
    result = {"source_filename": "sample.txt", "content_hash": "hash-a", "original_dna_sequence": "ACGT"}
    assert result_matches(FILE_A, result, "original_dna_sequence", "ACGT") is True


def test_result_matches_fails_on_dna_sequence_mismatch_even_if_identity_matches():
    result = {"source_filename": "sample.txt", "content_hash": "hash-a", "original_dna_sequence": "ACGT"}
    assert result_matches(FILE_A, result, "original_dna_sequence", "TTTT") is False


def test_result_matches_fails_on_identity_mismatch_even_if_dna_sequence_matches():
    result = {"source_filename": "sample.txt", "content_hash": "hash-a", "original_dna_sequence": "ACGT"}
    assert result_matches(FILE_B_SAME_NAME_DIFFERENT_CONTENT, result, "original_dna_sequence", "ACGT") is False


def test_result_matches_without_dna_field_only_checks_identity():
    result = {"source_filename": "sample.txt", "content_hash": "hash-a"}
    assert result_matches(FILE_A, result) is True


def test_result_matches_handles_none_result_safely():
    assert result_matches(FILE_A, None, "original_dna_sequence", "ACGT") is False


def test_result_matches_handles_none_file_info_safely():
    result = {"source_filename": "sample.txt", "content_hash": "hash-a", "original_dna_sequence": "ACGT"}
    assert result_matches(None, result, "original_dna_sequence", "ACGT") is False
