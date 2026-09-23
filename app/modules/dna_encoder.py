"""
DNA encoding logic (non-UI, no Streamlit dependency).

This module converts raw file bytes into a binary string, and that
binary string into a simulated DNA base sequence (A, T, G, C). It is
kept completely independent of Streamlit so it can be imported and
unit-tested on its own, and reused later by the decoder (Phase 4) and
mutation simulator (Phase 5).

ENCODING SCHEME (2 bits per DNA base)
--------------------------------------
Each byte of the file is 8 bits, which we split into four 2-bit
chunks. Each 2-bit chunk is mapped to one DNA base using a fixed,
reversible table:

    00 -> A
    01 -> C
    10 -> G
    11 -> T

This is a simple *educational* scheme (not the encoding used by real
commercial DNA-storage systems). Because 1 byte = 8 bits = four 2-bit
chunks, every byte always maps to exactly 4 DNA bases with no padding
ever required -- the binary length is always a multiple of 2 already.
"""

from collections import Counter

# Fixed, documented 2-bit -> base mapping. BASE_TO_BITS is simply the
# reverse of this, built automatically so the two can never drift out
# of sync with each other.
BITS_TO_BASE = {
    "00": "A",
    "01": "C",
    "10": "G",
    "11": "T",
}
BASE_TO_BITS = {base: bits for bits, base in BITS_TO_BASE.items()}

BITS_PER_BASE = 2


class DNAEncodingError(Exception):
    """Raised when file bytes cannot be encoded into DNA."""


def bytes_to_binary(data: bytes) -> str:
    """Convert raw bytes into a binary string (e.g. b'A' -> '01000001').

    Each byte becomes exactly 8 characters ('0'/'1'), so the resulting
    string's length is always len(data) * 8 -- no bits are ever lost.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise DNAEncodingError("Input must be bytes to convert to binary.")

    return "".join(format(byte, "08b") for byte in data)


def binary_to_dna(binary_str: str) -> str:
    """Convert a binary string into a DNA base sequence.

    Reads the binary string in 2-bit chunks and maps each chunk to a
    base using BITS_TO_BASE. Because bytes_to_binary() always produces
    a length that's a multiple of 8 (and therefore a multiple of 2),
    no padding is needed here for file-derived data. As a safety net
    for any other caller, an odd-length string is rejected explicitly
    rather than silently dropping a bit.
    """
    if not isinstance(binary_str, str) or any(c not in "01" for c in binary_str):
        raise DNAEncodingError("Binary data must be a string containing only '0' and '1'.")

    if len(binary_str) % BITS_PER_BASE != 0:
        raise DNAEncodingError(
            "Binary length must be a multiple of 2 to encode into DNA bases "
            "without losing bits."
        )

    bases = [
        BITS_TO_BASE[binary_str[i : i + BITS_PER_BASE]]
        for i in range(0, len(binary_str), BITS_PER_BASE)
    ]
    return "".join(bases)


def count_bases(dna_sequence: str) -> dict:
    """Return a count of each base (A, T, G, C) in the sequence.

    Bases with zero occurrences are still included (as 0) so the UI
    can always display all four bars/metrics consistently.
    """
    counts = Counter(dna_sequence)
    return {base: counts.get(base, 0) for base in BITS_TO_BASE.values()}


def encode_file_to_dna(data: bytes) -> dict:
    """Run the full pipeline: bytes -> binary -> DNA, plus statistics.

    Returns a dict containing everything the UI needs to display,
    so the Streamlit page stays a thin presentation layer.
    """
    if data is None:
        raise DNAEncodingError("No file data was provided to encode.")

    binary_str = bytes_to_binary(data)
    dna_sequence = binary_to_dna(binary_str)
    base_counts = count_bases(dna_sequence)

    return {
        "original_size_bytes": len(data),
        "binary_length_bits": len(binary_str),
        "binary_str": binary_str,
        "dna_sequence": dna_sequence,
        "dna_length": len(dna_sequence),
        "bits_per_base": BITS_PER_BASE,
        "base_counts": base_counts,
    }
