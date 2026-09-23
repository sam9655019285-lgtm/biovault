"""
DNA storage efficiency & compression analysis logic (non-UI, no
Streamlit dependency).

This module computes simple, transparent statistics about the Phase 3
encoding scheme's theoretical DNA storage characteristics: how binary
data maps to DNA bases, how much redundancy Phase 6's error-correction
scheme adds, and how a Phase 5 mutation changed the sequence length.

IMPORTANT: All numbers here are *computational estimates* based purely
on this project's own encoding/redundancy math. They do NOT model real
DNA synthesis cost, sequencing cost, primers, addressing/indexing
metadata, or any other real-world DNA storage overhead. DNA storage is
NOT automatically smaller or more efficient than ordinary binary
storage -- see the "raw efficiency" explanation below.

ENCODING RECAP (from dna_encoder.py, Phase 3)
-------------------------------------------------
    00 -> A   01 -> C   10 -> G   11 -> T

Each DNA base represents exactly 2 bits, so 4 bases represent 1 byte.
Because file-derived binary data is always a multiple of 8 bits (every
byte is 8 bits), it is always also a multiple of 2 bits -- so this
scheme never needs padding, and the DNA sequence length is always
exactly (binary_length_bits / 2).

RAW EFFICIENCY
------------------
"Raw theoretical efficiency" here means:

    (original data bits / encoded DNA storage bits) x 100

where "encoded DNA storage bits" = dna_length x 2 (each base can only
express 2 bits, whether or not that base is doing "useful" work). For
this project's scheme, since no padding is ever added, this raw
efficiency is always exactly 100% -- but that only reflects that the
DNA sequence isn't wasting any of its own 2-bit-per-base capacity. It
is NOT a claim that DNA is more compact than the original file: 1 DNA
base (2 bits of capacity) is smaller than 1 byte (8 bits), so 4 DNA
bases are needed to store what 1 byte already stores. DNA storage here
is not a compression scheme.
"""

DNA_BASES_PER_BYTE = 4  # 8 bits / 2 bits-per-base
BITS_PER_BASE = 2
BITS_PER_BYTE = 8

BYTE_UNITS = ("B", "KB", "MB", "GB", "TB")


class StorageAnalysisError(Exception):
    """Raised when storage-analysis inputs are invalid."""


def _validate_non_negative_int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise StorageAnalysisError(f"{name} must be a non-negative whole number.")
    return value


def calculate_binary_size(file_bytes: bytes) -> dict:
    """Return the size of file bytes in bytes and in bits.

    A zero-byte file is valid input and simply produces 0 bits.
    """
    if not isinstance(file_bytes, (bytes, bytearray)):
        raise StorageAnalysisError("file_bytes must be a bytes object.")

    size_bytes = len(file_bytes)
    return {
        "size_bytes": size_bytes,
        "size_bits": size_bytes * BITS_PER_BYTE,
    }


def calculate_dna_size(binary_length_bits: int) -> dict:
    """Return how many DNA bases are required to encode this many bits.

    Requires an even number of bits since each base carries 2 bits;
    file-derived binary is always even (a multiple of 8), but this is
    still validated explicitly rather than silently rounding.
    """
    _validate_non_negative_int(binary_length_bits, "binary_length_bits")
    if binary_length_bits % BITS_PER_BASE != 0:
        raise StorageAnalysisError(
            f"binary_length_bits ({binary_length_bits}) must be a multiple of "
            f"{BITS_PER_BASE} to convert evenly into DNA bases."
        )

    return {
        "binary_length_bits": binary_length_bits,
        "dna_bases_required": binary_length_bits // BITS_PER_BASE,
    }


def calculate_dna_capacity(dna_length: int) -> dict:
    """Return the theoretical raw storage capacity of a DNA sequence.

    Theoretical capacity assumes every base is used at its full 2-bit
    capacity -- it does not account for redundancy/error-correction
    bases, which reduce the *usable* capacity for original data.
    """
    _validate_non_negative_int(dna_length, "dna_length")
    capacity_bits = dna_length * BITS_PER_BASE
    return {
        "dna_length": dna_length,
        "capacity_bits": capacity_bits,
        "capacity_bytes": capacity_bits / BITS_PER_BYTE,
    }


def calculate_raw_efficiency(data_bits: int, dna_storage_bits: int) -> float:
    """Return (data_bits / dna_storage_bits) * 100, as a percentage.

    Returns 0.0 for a zero-length sequence rather than raising a
    division-by-zero error, since "no data, no DNA" is a valid,
    well-defined empty case (0% is meaningless either way, but this
    avoids crashing the analysis page for an empty upload).
    """
    _validate_non_negative_int(data_bits, "data_bits")
    _validate_non_negative_int(dna_storage_bits, "dna_storage_bits")

    if dna_storage_bits == 0:
        return 0.0

    return round((data_bits / dna_storage_bits) * 100, 2)


def calculate_encoding_overhead(expected_dna_length: int, actual_dna_length: int) -> dict:
    """Compare the DNA length predicted from binary math to the actual
    encoded length (a sanity-check; for this project's fixed 2-bit
    scheme these should always match exactly, with zero overhead).
    """
    _validate_non_negative_int(expected_dna_length, "expected_dna_length")
    _validate_non_negative_int(actual_dna_length, "actual_dna_length")

    difference_bases = actual_dna_length - expected_dna_length
    difference_percent = (
        round((difference_bases / expected_dna_length) * 100, 2)
        if expected_dna_length > 0
        else 0.0
    )

    return {
        "expected_dna_length": expected_dna_length,
        "actual_dna_length": actual_dna_length,
        "difference_bases": difference_bases,
        "difference_percent": difference_percent,
    }


def calculate_redundancy_overhead(dna_length: int, block_size: int, redundancy_size: int) -> dict:
    """Calculate how many extra bases Phase 6's redundancy scheme adds.

    Mirrors the same block-count math used by
    dna_error_correction.add_redundancy() (ceiling division of
    dna_length by block_size), so the numbers shown here always match
    what that module would actually produce. Smaller blocks mean more
    blocks for the same data, and therefore more total redundancy
    bases (since each block gets its own redundancy_size copies).
    """
    _validate_non_negative_int(dna_length, "dna_length")
    if isinstance(block_size, bool) or not isinstance(block_size, int) or block_size < 1:
        raise StorageAnalysisError("block_size must be a positive whole number.")
    if isinstance(redundancy_size, bool) or not isinstance(redundancy_size, int) or redundancy_size < 1:
        raise StorageAnalysisError("redundancy_size must be a positive whole number.")

    if dna_length == 0:
        num_blocks = 0
    else:
        num_blocks = (dna_length + block_size - 1) // block_size  # ceiling division

    redundancy_bases = num_blocks * redundancy_size
    protected_length = dna_length + redundancy_bases
    overhead_percent = (
        round((redundancy_bases / dna_length) * 100, 2) if dna_length > 0 else 0.0
    )

    return {
        "dna_length": dna_length,
        "block_size": block_size,
        "redundancy_size": redundancy_size,
        "num_blocks": num_blocks,
        "redundancy_bases": redundancy_bases,
        "protected_length": protected_length,
        "overhead_percent": overhead_percent,
    }


def calculate_mutation_impact(mutation_stats: dict) -> dict:
    """Summarize how a Phase 5 mutation changed sequence length.

    `mutation_stats` is expected to be the stats dict produced by
    dna_mutator.mutate_dna() (or the "stats" entry of the Mutation
    Simulator's stored session-state result) -- this function never
    invents mutation data; if the required fields aren't present, it
    raises rather than guessing.
    """
    required_fields = {"original_length", "mutated_length", "mutation_type", "mutation_rate", "total_edits"}
    if not isinstance(mutation_stats, dict) or not required_fields <= set(mutation_stats.keys()):
        raise StorageAnalysisError(
            "mutation_stats is missing required fields: "
            f"{', '.join(sorted(required_fields))}."
        )

    length_difference = mutation_stats["mutated_length"] - mutation_stats["original_length"]

    return {
        "original_length": mutation_stats["original_length"],
        "mutated_length": mutation_stats["mutated_length"],
        "mutation_type": mutation_stats["mutation_type"],
        "mutation_rate": mutation_stats["mutation_rate"],
        "total_edits": mutation_stats["total_edits"],
        "length_difference": length_difference,
        "length_changed": length_difference != 0,
    }


def format_bytes(num_bytes) -> str:
    """Return a human-readable byte size string, e.g. '512 B', '1.25 KB'."""
    if isinstance(num_bytes, bool) or not isinstance(num_bytes, (int, float)) or num_bytes < 0:
        raise StorageAnalysisError("num_bytes must be a non-negative number.")

    value = float(num_bytes)
    for unit in BYTE_UNITS:
        if value < 1024 or unit == BYTE_UNITS[-1]:
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.2f} {unit}"
        value /= 1024

    return f"{value:.2f} {BYTE_UNITS[-1]}"  # unreachable safeguard


def analyze_storage_efficiency(
    file_size_bytes: int,
    dna_length: int,
    block_size: int = None,
    redundancy_size: int = None,
    mutation_stats: dict = None,
) -> dict:
    """Build a full, structured storage-analysis report.

    Combines all the calculations above into one dict with clearly
    named sections, so the UI layer can stay a thin presentation layer.
    redundancy/mutation sections are only included when their inputs
    are provided -- this function never invents data for a section
    that wasn't requested or isn't available.
    """
    # file_size_bytes may be passed as raw bytes or as an already-known size.
    if isinstance(file_size_bytes, (bytes, bytearray)):
        file_size = len(file_size_bytes)
    else:
        file_size = _validate_non_negative_int(file_size_bytes, "file_size_bytes")

    binary_info = {"size_bytes": file_size, "size_bits": file_size * BITS_PER_BYTE}
    dna_size_info = calculate_dna_size(binary_info["size_bits"])
    capacity_info = calculate_dna_capacity(dna_length)
    encoding_overhead = calculate_encoding_overhead(dna_size_info["dna_bases_required"], dna_length)
    raw_efficiency = calculate_raw_efficiency(binary_info["size_bits"], dna_length * BITS_PER_BASE)

    report = {
        "file_size_bytes": file_size,
        "binary_info": binary_info,
        "dna_size_info": dna_size_info,
        "capacity_info": capacity_info,
        "encoding_overhead": encoding_overhead,
        "raw_efficiency_percent": raw_efficiency,
        "redundancy_info": None,
        "mutation_info": None,
    }

    if block_size is not None and redundancy_size is not None:
        report["redundancy_info"] = calculate_redundancy_overhead(dna_length, block_size, redundancy_size)

    if mutation_stats is not None:
        report["mutation_info"] = calculate_mutation_impact(mutation_stats)

    return report
