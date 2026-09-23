"""
Tests for app/modules/dna_decoder.py.

Plain-Python tests (no Streamlit), covering decoding, validation, and
round-trip recovery against the Phase 3 encoder.
Run with:  python -m pytest
"""

import pytest

from app.modules.dna_encoder import bytes_to_binary, binary_to_dna, encode_file_to_dna
from app.modules.dna_decoder import (
    DNADecodingError,
    validate_dna_sequence,
    dna_to_binary,
    binary_to_bytes,
    decode_dna_to_file,
    compare_bytes,
)


# 1. Empty DNA sequence -----------------------------------------------------

def test_empty_dna_sequence_is_rejected():
    with pytest.raises(DNADecodingError):
        validate_dna_sequence("")


# 2. Invalid DNA characters --------------------------------------------------

def test_invalid_characters_are_rejected():
    with pytest.raises(DNADecodingError):
        validate_dna_sequence("ACGTX")


def test_non_string_input_is_rejected():
    with pytest.raises(DNADecodingError):
        validate_dna_sequence(1234)  # type: ignore[arg-type]


# 3. Lowercase DNA input ------------------------------------------------------

def test_lowercase_input_is_normalized_to_uppercase():
    assert validate_dna_sequence("acgt") == "ACGT"


def test_mixed_case_input_is_normalized():
    assert validate_dna_sequence("AcGt") == "ACGT"


# 4. Known DNA sequence decoding ----------------------------------------------

def test_known_sequence_decodes_to_expected_binary():
    # CAAC -> 01 00 00 01 -> '01000001' which is 'A' (0x41)
    assert dna_to_binary("CAAC") == "01000001"


def test_known_sequence_decodes_to_original_byte():
    recovered = binary_to_bytes(dna_to_binary("CAAC"))
    assert recovered == b"A"


# 5. DNA-to-binary conversion --------------------------------------------------

def test_dna_to_binary_maps_every_base():
    assert dna_to_binary("ACGT") == "00011011"


# 6. Binary-to-bytes conversion -----------------------------------------------

def test_binary_to_bytes_handles_empty_string():
    assert binary_to_bytes("") == b""


def test_binary_to_bytes_converts_multiple_bytes():
    binary_str = bytes_to_binary(b"Hi")
    assert binary_to_bytes(binary_str) == b"Hi"


# 7. Invalid binary lengths ----------------------------------------------------

def test_binary_length_not_multiple_of_8_is_rejected():
    with pytest.raises(DNADecodingError):
        binary_to_bytes("0000001")  # 7 bits


def test_binary_with_non_binary_characters_is_rejected():
    with pytest.raises(DNADecodingError):
        binary_to_bytes("00000002")


# 8. Round-trip encoding -> decoding for known byte sequences -----------------

@pytest.mark.parametrize("original", [b"A", b"Hi", b"Hello, BioVault!", b"\x00\xff\x10"])
def test_round_trip_known_sequences(original):
    binary_str = bytes_to_binary(original)
    dna = binary_to_dna(binary_str)

    decoded_binary = dna_to_binary(dna)
    recovered = binary_to_bytes(decoded_binary)

    assert recovered == original


# 9. Round-trip recovery for several small byte sequences ----------------------

@pytest.mark.parametrize(
    "original",
    [
        b"x",
        b"DNA storage demo",
        bytes(range(0, 32)),
        bytes([0, 255, 128, 64, 1]),
    ],
)
def test_round_trip_recovery_via_full_pipeline(original):
    encoded = encode_file_to_dna(original)
    decoded = decode_dna_to_file(encoded["dna_sequence"])

    assert decoded["recovered_bytes"] == original
    comparison = compare_bytes(original, decoded["recovered_bytes"])
    assert comparison["is_identical"]
    assert comparison["differing_bytes"] == 0


# 10. Empty bytes handling ------------------------------------------------------

def test_encode_then_decode_empty_bytes():
    encoded = encode_file_to_dna(b"")
    assert encoded["dna_sequence"] == ""
    with pytest.raises(DNADecodingError):
        # An empty DNA sequence is explicitly rejected by the decoder
        # (there's nothing meaningful to decode), even though empty
        # bytes are a valid *encoder* input.
        decode_dna_to_file(encoded["dna_sequence"])


# 11. Corrupted or invalid DNA sequence handling ---------------------------------

def test_corrupted_dna_sequence_raises_clear_error():
    valid_dna = binary_to_dna(bytes_to_binary(b"Hi"))
    corrupted = valid_dna[:-1] + "Z"  # replace last base with invalid char
    with pytest.raises(DNADecodingError):
        decode_dna_to_file(corrupted)


def test_truncated_dna_sequence_with_bad_length_raises_error():
    # 3 bases -> 6 bits, not a multiple of 8 -> cannot form whole bytes.
    with pytest.raises(DNADecodingError):
        decode_dna_to_file("ACG")


# 12. Exact byte-for-byte comparison ---------------------------------------------

def test_compare_bytes_identical():
    result = compare_bytes(b"hello", b"hello")
    assert result["is_identical"]
    assert result["differing_bytes"] == 0


def test_compare_bytes_detects_single_byte_difference():
    result = compare_bytes(b"hello", b"hEllo")
    assert not result["is_identical"]
    assert result["differing_bytes"] == 1


def test_compare_bytes_does_not_assume_success_from_matching_size():
    # Same length, different content -- must NOT report identical.
    result = compare_bytes(b"AAAA", b"AAAB")
    assert not result["is_identical"]
    assert result["differing_bytes"] == 1


def test_compare_bytes_counts_length_mismatch_as_differences():
    result = compare_bytes(b"hello", b"hell")
    assert not result["is_identical"]
    assert result["differing_bytes"] == 1  # one missing trailing byte
