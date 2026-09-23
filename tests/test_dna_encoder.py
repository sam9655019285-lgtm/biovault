"""
Tests for app/modules/dna_encoder.py.

These tests only exercise plain Python functions (no Streamlit), which
is exactly why dna_encoder.py was kept free of any `import streamlit`.
Run with:  python -m pytest
"""

import pytest

from app.modules.dna_encoder import (
    DNAEncodingError,
    bytes_to_binary,
    binary_to_dna,
    count_bases,
    encode_file_to_dna,
    BITS_TO_BASE,
    BASE_TO_BITS,
)


# 1. Empty bytes -----------------------------------------------------------

def test_empty_bytes_produces_empty_binary_and_dna():
    result = encode_file_to_dna(b"")
    assert result["original_size_bytes"] == 0
    assert result["binary_str"] == ""
    assert result["dna_sequence"] == ""
    assert result["dna_length"] == 0
    assert result["base_counts"] == {"A": 0, "T": 0, "G": 0, "C": 0}


# 2. A small known byte sequence -------------------------------------------

def test_known_byte_sequence_encodes_correctly():
    # Letter 'A' is 0x41 = 01000001 in binary.
    # Split into 2-bit chunks: 01 00 00 01 -> C A A C
    data = b"A"
    binary_str = bytes_to_binary(data)
    assert binary_str == "01000001"

    dna = binary_to_dna(binary_str)
    assert dna == "CAAC"


# 3. Binary-to-DNA conversion (general) -------------------------------------

def test_binary_to_dna_maps_every_2_bit_chunk():
    binary_str = "00011011"  # A C G T
    assert binary_to_dna(binary_str) == "ACGT"


# 4. DNA base mapping correctness --------------------------------------------

def test_mapping_table_is_consistent_and_reversible():
    assert BITS_TO_BASE == {"00": "A", "01": "C", "10": "G", "11": "T"}
    # BASE_TO_BITS must be the exact reverse of BITS_TO_BASE.
    for bits, base in BITS_TO_BASE.items():
        assert BASE_TO_BITS[base] == bits
    assert len(BITS_TO_BASE) == 4
    assert len(set(BITS_TO_BASE.values())) == 4  # all bases unique


# 5. Even and odd binary lengths ---------------------------------------------

def test_even_length_binary_is_accepted():
    # 4 bits -> 2 bases, no error.
    assert binary_to_dna("0011") == "AT"


def test_odd_length_binary_is_rejected_not_silently_truncated():
    with pytest.raises(DNAEncodingError):
        binary_to_dna("001")  # 3 bits, cannot map cleanly to bases


def test_file_derived_binary_is_always_even_length():
    # Every byte -> 8 bits, so any byte string produces a binary
    # string whose length is a multiple of 8 (and thus of 2).
    for size in (0, 1, 2, 3, 7, 16):
        data = bytes(range(size))
        binary_str = bytes_to_binary(data)
        assert len(binary_str) % 2 == 0
        assert len(binary_str) == size * 8


# 6. Round-trip preparation for future decoding -------------------------------

def test_round_trip_bits_can_be_reconstructed_from_dna():
    # This doesn't test the (future) decoder module, but confirms the
    # encoding is information-preserving: reversing BITS_TO_BASE on the
    # DNA sequence gives back the exact original binary string.
    original_data = b"Hi!"
    binary_str = bytes_to_binary(original_data)
    dna = binary_to_dna(binary_str)

    rebuilt_binary = "".join(BASE_TO_BITS[base] for base in dna)
    assert rebuilt_binary == binary_str

    rebuilt_bytes = bytes(
        int(rebuilt_binary[i : i + 8], 2) for i in range(0, len(rebuilt_binary), 8)
    )
    assert rebuilt_bytes == original_data


# 7. Invalid input handling ---------------------------------------------------

def test_bytes_to_binary_rejects_non_bytes_input():
    with pytest.raises(DNAEncodingError):
        bytes_to_binary("not bytes")  # type: ignore[arg-type]


def test_binary_to_dna_rejects_non_binary_characters():
    with pytest.raises(DNAEncodingError):
        binary_to_dna("01102")  # '2' is not a valid bit


def test_encode_file_to_dna_rejects_none_input():
    with pytest.raises(DNAEncodingError):
        encode_file_to_dna(None)


def test_count_bases_includes_zero_counts_for_missing_bases():
    counts = count_bases("AAAA")
    assert counts == {"A": 4, "T": 0, "G": 0, "C": 0}
