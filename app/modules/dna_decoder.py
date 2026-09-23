"""
DNA decoding logic (non-UI, no Streamlit dependency).

This module reverses the pipeline from dna_encoder.py: it turns a DNA
base sequence back into a binary string, and that binary string back
into the original file bytes. It intentionally reuses the exact same
mapping table object as the encoder (BASE_TO_BITS from dna_encoder.py)
so the two modules can never drift out of sync with each other.

DECODING SCHEME (reverse of Phase 3's 2-bit encoding)
-------------------------------------------------------
    A -> 00
    C -> 01
    G -> 10
    T -> 11

Each DNA base represents one 2-bit chunk. Four bases (8 bits) always
reconstruct exactly one original byte. This module never "repairs" or
guesses at invalid data -- if the DNA sequence contains characters
outside A/T/G/C, or the resulting binary length isn't a multiple of 8,
decoding fails loudly with a clear error instead of silently producing
wrong bytes.
"""

from app.modules.dna_encoder import BASE_TO_BITS, BITS_PER_BASE

VALID_BASES = set(BASE_TO_BITS.keys())  # {"A", "C", "G", "T"}
BITS_PER_BYTE = 8


class DNADecodingError(Exception):
    """Raised when a DNA sequence or binary string cannot be decoded."""


def validate_dna_sequence(dna_sequence: str) -> str:
    """Validate a DNA sequence and return it normalized to uppercase.

    Rules:
    - Must be a non-empty string.
    - Lowercase letters (a/t/g/c) are accepted and normalized to
      uppercase, since case carries no information in this scheme.
    - Any character outside A/T/G/C is rejected -- we do not strip,
      skip, or "fix" bad characters, since that would silently change
      the data being decoded.
    """
    if not isinstance(dna_sequence, str):
        raise DNADecodingError("DNA sequence must be a string.")

    if len(dna_sequence) == 0:
        raise DNADecodingError("DNA sequence is empty -- nothing to decode.")

    normalized = dna_sequence.upper()

    invalid_chars = sorted(set(normalized) - VALID_BASES)
    if invalid_chars:
        raise DNADecodingError(
            "DNA sequence contains invalid character(s): "
            f"{', '.join(repr(c) for c in invalid_chars)}. "
            "Only A, T, G, C (any case) are allowed."
        )

    return normalized


def dna_to_binary(dna_sequence: str) -> str:
    """Convert a validated DNA sequence into a binary string.

    Each base is mapped back to its 2-bit chunk using BASE_TO_BITS,
    the exact reverse of the encoder's BITS_TO_BASE table.
    """
    normalized = validate_dna_sequence(dna_sequence)
    return "".join(BASE_TO_BITS[base] for base in normalized)


def binary_to_bytes(binary_str: str) -> bytes:
    """Convert a binary string back into bytes.

    The binary length must be an exact multiple of 8 (1 byte = 8
    bits). If it isn't, we refuse to guess/pad -- that would silently
    invent or drop data -- and raise a clear error instead.
    """
    if not isinstance(binary_str, str) or any(c not in "01" for c in binary_str):
        raise DNADecodingError("Binary data must be a string containing only '0' and '1'.")

    if len(binary_str) % BITS_PER_BYTE != 0:
        raise DNADecodingError(
            f"Binary length ({len(binary_str)} bits) is not a multiple of 8, "
            "so it cannot be reassembled into whole bytes without guessing "
            "at missing/extra bits."
        )

    if len(binary_str) == 0:
        return b""

    byte_values = [
        int(binary_str[i : i + BITS_PER_BYTE], 2)
        for i in range(0, len(binary_str), BITS_PER_BYTE)
    ]
    return bytes(byte_values)


def decode_dna_to_file(dna_sequence: str) -> dict:
    """Run the full reverse pipeline: DNA -> binary -> original bytes.

    Returns a dict with the recovered bytes plus stats the UI needs,
    keeping ui_dna_decoding.py a thin presentation layer, mirroring
    encode_file_to_dna() in dna_encoder.py.
    """
    binary_str = dna_to_binary(dna_sequence)
    recovered_bytes = binary_to_bytes(binary_str)

    return {
        "dna_length": len(dna_sequence),
        "binary_length_bits": len(binary_str),
        "binary_str": binary_str,
        "recovered_bytes": recovered_bytes,
        "recovered_size_bytes": len(recovered_bytes),
    }


def compare_bytes(original: bytes, recovered: bytes) -> dict:
    """Byte-for-byte comparison of original vs recovered data.

    Never concludes success from matching sizes alone -- it walks the
    shorter of the two lengths comparing byte-by-byte, and also counts
    any extra trailing bytes on the longer side as differences.
    """
    if not isinstance(original, (bytes, bytearray)) or not isinstance(
        recovered, (bytes, bytearray)
    ):
        raise DNADecodingError("Both original and recovered data must be bytes.")

    min_len = min(len(original), len(recovered))
    differing_bytes = sum(
        1 for i in range(min_len) if original[i] != recovered[i]
    )
    # Any length mismatch means every "extra" byte on the longer side
    # also counts as a difference -- sizes matching is not sufficient
    # for a "success" claim.
    differing_bytes += abs(len(original) - len(recovered))

    is_identical = (len(original) == len(recovered)) and (differing_bytes == 0)

    return {
        "original_size_bytes": len(original),
        "recovered_size_bytes": len(recovered),
        "is_identical": is_identical,
        "differing_bytes": differing_bytes,
    }
