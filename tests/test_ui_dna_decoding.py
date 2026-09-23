"""
Regression tests for app/modules/ui_dna_decoding.py's stale-result guard.

These test the pure `_decoding_result_matches` helper directly (plain
dicts, no Streamlit session needed) -- it decides whether a previously
stored decoding result may still be displayed for the current file/DNA
encoding, or whether it's stale and must be hidden.

Regression for Phase 13 bug: the decoding page used to only compare
`source_filename`, so a stale decoding result from a previous DNA
sequence could be shown as if it matched a newly re-encoded sequence
for the same filename.

Phase 14 update: `_decoding_result_matches` now relies on
`file_identity_matches` (filename + content_hash), so every dict here
also carries a "content_hash" field, exactly as the real UI code
attaches one via file_handler.compute_content_hash().
"""

from app.modules.ui_dna_decoding import _decoding_result_matches


def test_matches_when_filename_hash_and_dna_sequence_agree():
    file_info = {"filename": "a.txt", "content_hash": "hash-a"}
    encoding_result = {"dna_sequence": "ACGT"}
    decoding_result = {"source_filename": "a.txt", "content_hash": "hash-a", "source_dna_sequence": "ACGT"}

    assert _decoding_result_matches(file_info, encoding_result, decoding_result) is True


def test_does_not_match_when_dna_sequence_changed_for_same_filename():
    # Same filename, but the file was re-encoded (e.g. a different file
    # with the same name was uploaded and re-encoded), producing a new
    # DNA sequence. The old decoding result must be treated as stale.
    file_info = {"filename": "a.txt", "content_hash": "hash-a"}
    encoding_result = {"dna_sequence": "TTTT"}  # newly re-encoded sequence
    decoding_result = {"source_filename": "a.txt", "content_hash": "hash-a", "source_dna_sequence": "ACGT"}  # stale

    assert _decoding_result_matches(file_info, encoding_result, decoding_result) is False


def test_does_not_match_when_filename_differs():
    file_info = {"filename": "b.txt", "content_hash": "hash-b"}
    encoding_result = {"dna_sequence": "ACGT"}
    decoding_result = {"source_filename": "a.txt", "content_hash": "hash-a", "source_dna_sequence": "ACGT"}

    assert _decoding_result_matches(file_info, encoding_result, decoding_result) is False


def test_does_not_match_legacy_result_missing_dna_sequence_field():
    # A decoding_result stored before this fix (or a failed-decode
    # result) has no "source_dna_sequence" key -- must not match.
    file_info = {"filename": "a.txt", "content_hash": "hash-a"}
    encoding_result = {"dna_sequence": "ACGT"}
    decoding_result = {"source_filename": "a.txt", "content_hash": "hash-a"}

    assert _decoding_result_matches(file_info, encoding_result, decoding_result) is False


def test_same_filename_different_content_hash_never_matches():
    # Phase 14 core scenario: a different file uploaded under the same
    # filename must never be treated as matching the old decoding result,
    # even if a legacy-style dict happened to share the same filename.
    file_info = {"filename": "a.txt", "content_hash": "hash-b"}  # a different file, same name
    encoding_result = {"dna_sequence": "ACGT"}
    decoding_result = {"source_filename": "a.txt", "content_hash": "hash-a", "source_dna_sequence": "ACGT"}

    assert _decoding_result_matches(file_info, encoding_result, decoding_result) is False


def test_legacy_decoding_result_missing_content_hash_never_matches():
    # A decoding_result stored before Phase 14 has no "content_hash" key
    # at all -- treated as unverifiable, never shown as current.
    file_info = {"filename": "a.txt", "content_hash": "hash-a"}
    encoding_result = {"dna_sequence": "ACGT"}
    decoding_result = {"source_filename": "a.txt", "source_dna_sequence": "ACGT"}  # no content_hash

    assert _decoding_result_matches(file_info, encoding_result, decoding_result) is False
