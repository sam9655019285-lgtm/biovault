"""
DNA storage capacity, information density, and cost/scale comparison
logic (non-UI, no Streamlit dependency).

EDUCATIONAL MODULE ONLY. This module never claims that its numbers
represent real laboratory DNA-storage performance, current commercial
pricing, or a validated physical measurement. Every value it returns
is labeled with a `category`:

- "theoretical" : pure math from the 4-symbol DNA alphabet (2 bits/base
                  = log2(4)), before any real-world constraint.
- "measured"    : an actual value taken from the user's uploaded file
                  or BioVault's own real encoding result.
- "measured_vs_theoretical": a comparison mixing a measured value
                  against the theoretical ideal (e.g. actual vs.
                  theoretical DNA length) -- never presented as if it
                  were a single kind of value.
- "estimated"   : a number computed from USER-SUPPLIED or clearly
                  documented example assumptions (cost, physical mass)
                  -- never a claimed fact.

This module reuses existing, already-tested calculations instead of
redefining them, so BioVault never has two disagreeing formulas for
the same concept:
- storage_analysis.calculate_encoding_overhead() for actual-vs-expected
  DNA length comparisons.
- storage_analysis.calculate_redundancy_overhead() for Phase 6's
  checksum-based error-correction overhead.
- redundancy_simulation.calculate_storage_overhead() for Phase 18's
  whole-copy redundancy overhead.
- dna_encoder.BITS_PER_BASE for the encoding's bits-per-base constant.

PERFORMANCE SAFETY: every function here works with integers/floats
only -- it never builds an actual DNA string, even for petabyte-scale
examples. A "1 PB" example is just a Python integer computation, not a
multi-quadrillion-character string.
"""

from app.modules.dna_encoder import BITS_PER_BASE
from app.modules.storage_analysis import (
    DNA_BASES_PER_BYTE,
    StorageAnalysisError,
    calculate_encoding_overhead,
    calculate_redundancy_overhead as _error_correction_overhead,
)
from app.modules.redundancy_simulation import (
    RedundancySimulationError,
    calculate_storage_overhead as _copy_redundancy_overhead,
)

BITS_PER_BYTE = 8
BYTES_PER_BASE_THEORETICAL = BITS_PER_BASE / BITS_PER_BYTE  # 0.25

# Binary unit sizes (1 KB = 1024 bytes), used consistently throughout
# this module -- always labeled explicitly wherever displayed.
BINARY_UNITS = {
    "B": 1,
    "KB": 1024,
    "MB": 1024**2,
    "GB": 1024**3,
    "TB": 1024**4,
    "PB": 1024**5,
}

# 1 Dalton (unified atomic mass unit) in grams -- a standard physical
# constant, not an assumption. The molecular-weight-per-base VALUE
# multiplied by this constant IS an assumption (see estimate_dna_mass).
DALTON_TO_GRAMS = 1.66053906660e-24

# A commonly cited APPROXIMATE average molecular weight for a single
# DNA nucleotide (varies by base identity, strand form, and buffer/salt
# conditions in reality) -- provided only as a documented example
# default, never as a precise or authoritative constant.
DEFAULT_AVERAGE_BASE_WEIGHT_DALTONS = 330.0

# Illustrative-only conventional-storage size examples (section 10).
CONVENTIONAL_STORAGE_EXAMPLES_BYTES = {
    "1 TB": 1 * 1024**4,
    "10 TB": 10 * 1024**4,
    "100 TB": 100 * 1024**4,
    "1 PB": 1 * 1024**5,
}

# Illustrative-only scale examples (section 12).
SCALE_EXAMPLES_BYTES = {
    "1 MB file": 1 * 1024**2,
    "1 GB file": 1 * 1024**3,
    "1 TB data": 1 * 1024**4,
    "1 PB data": 1 * 1024**5,
}


class CapacityAnalysisError(Exception):
    """Raised when capacity-analysis inputs are invalid."""


def _validate_non_negative_number(value, name: str):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise CapacityAnalysisError(f"{name} must be a non-negative number.")
    return value


# --- 3. Basic DNA information-theory calculations --------------------------------

def bits_per_dna_base() -> float:
    """Return the theoretical information capacity of one DNA base.

    DNA has exactly 4 possible symbols (A, C, G, T). A symbol chosen
    from N equally likely possibilities carries log2(N) bits of
    information; log2(4) = 2. This is the SAME constant BioVault's
    real encoder already uses (dna_encoder.BITS_PER_BASE) -- reused
    here, not redefined, so the two can never disagree.
    """
    return float(BITS_PER_BASE)


def bytes_per_dna_base() -> float:
    """Return the theoretical byte-equivalent capacity of one DNA base
    (2 bits / 8 bits-per-byte = 0.25 bytes)."""
    return BYTES_PER_BASE_THEORETICAL


def dna_bases_required_for_bits(num_bits) -> float:
    """Return the theoretical number of DNA bases needed to represent
    `num_bits` bits, at the ideal 2-bits-per-base rate."""
    _validate_non_negative_number(num_bits, "num_bits")
    return num_bits / BITS_PER_BASE


def dna_bases_required_for_bytes(num_bytes) -> float:
    """Return the theoretical number of DNA bases needed to represent
    `num_bytes` bytes: bytes x 8 bits/byte / 2 bits/base = bytes x 4.

    This is the pure theoretical formula -- it does NOT read from, and
    may not exactly equal, BioVault's actual encoder output if the
    real encoder ever adds padding/overhead for a given input (for the
    current fixed 2-bit scheme it always matches exactly, since 1 byte
    is already evenly divisible into four 2-bit chunks -- see
    compare_actual_to_theoretical() to confirm this for real data).
    """
    _validate_non_negative_number(num_bytes, "num_bytes")
    return num_bytes * DNA_BASES_PER_BYTE


def digital_bytes_represented_by_dna_length(dna_length) -> float:
    """Return the theoretical number of bytes a DNA sequence of
    `dna_length` bases could represent, at the ideal 2-bits-per-base
    rate (the inverse of dna_bases_required_for_bytes())."""
    _validate_non_negative_number(dna_length, "dna_length")
    return dna_length / DNA_BASES_PER_BYTE


def theoretical_density_summary() -> dict:
    """Return the theoretical 2-bits/base capacity expressed in several
    common storage units, for display in the UI's "Information Density"
    section. All values are pure theoretical math -- see module
    docstring's category definitions.
    """
    bytes_per_base = BYTES_PER_BASE_THEORETICAL
    return {
        "possible_bases": 4,
        "bits_per_base": bits_per_dna_base(),
        "bytes_per_base": round(bytes_per_base, 4),
        "mb_per_million_bases": round((1_000_000 * bytes_per_base) / BINARY_UNITS["MB"], 6),
        "gb_per_billion_bases": round((1_000_000_000 * bytes_per_base) / BINARY_UNITS["GB"], 6),
        "tb_per_trillion_bases": round((1_000_000_000_000 * bytes_per_base) / BINARY_UNITS["TB"], 6),
        "category": "theoretical",
    }


# --- 4. File size -> DNA length calculator ----------------------------------------

def bytes_from_size(value, unit: str) -> float:
    """Convert `value` in the given binary `unit` (B/KB/MB/GB/TB/PB,
    1 KB = 1024 bytes) into a raw byte count."""
    _validate_non_negative_number(value, "value")
    if not isinstance(unit, str) or unit.upper() not in BINARY_UNITS:
        raise CapacityAnalysisError(
            f"Unknown unit {unit!r}. Must be one of: {', '.join(BINARY_UNITS)} (binary, 1 KB = 1024 bytes)."
        )
    return value * BINARY_UNITS[unit.upper()]


def calculate_theoretical_dna_requirement(value, unit: str) -> dict:
    """Return the theoretical DNA length needed to represent a file
    size given as `value` in `unit` (binary units)."""
    num_bytes = bytes_from_size(value, unit)
    theoretical_bases = dna_bases_required_for_bytes(num_bytes)

    return {
        "input_value": value,
        "input_unit": unit.upper(),
        "bytes": num_bytes,
        "theoretical_dna_bases": theoretical_bases,
        "bits_per_base": bits_per_dna_base(),
        "category": "theoretical",
    }


# --- 5. Actual encoded DNA vs. theoretical DNA ------------------------------------

def compare_actual_to_theoretical(file_size_bytes, actual_dna_length) -> dict:
    """Compare BioVault's REAL, actual encoded DNA length (from the
    existing dna_encoder.py -- the source of truth) against the pure
    THEORETICAL length for the same file size.

    Reuses storage_analysis.calculate_encoding_overhead() rather than
    recomputing the same overhead/difference formula a second way.
    `file_size_bytes` and `actual_dna_length` are expected to be real,
    measured values (e.g. from an uploaded file's encoding result).
    """
    _validate_non_negative_number(file_size_bytes, "file_size_bytes")
    if isinstance(actual_dna_length, bool) or not isinstance(actual_dna_length, int) or actual_dna_length < 0:
        raise CapacityAnalysisError("actual_dna_length must be a non-negative whole number.")

    theoretical_dna_length = int(dna_bases_required_for_bytes(file_size_bytes))

    try:
        overhead = calculate_encoding_overhead(theoretical_dna_length, actual_dna_length)
    except StorageAnalysisError as exc:
        raise CapacityAnalysisError(str(exc)) from exc

    effective_bits_per_base = (
        round((file_size_bytes * BITS_PER_BYTE) / actual_dna_length, 4) if actual_dna_length > 0 else 0.0
    )

    return {
        "file_size_bytes": file_size_bytes,
        "theoretical_dna_length": theoretical_dna_length,
        "actual_dna_length": actual_dna_length,
        "additional_bases": overhead["difference_bases"],
        "encoding_overhead_percent": overhead["difference_percent"],
        "effective_bits_per_base": effective_bits_per_base,
        "theoretical_bits_per_base": bits_per_dna_base(),
        "category": "measured_vs_theoretical",
    }


# --- 8. Redundancy overhead (Phase 18 whole-copy redundancy, reused) --------------

def calculate_copy_redundancy_overhead(dna_length: int, extra_copies: int) -> dict:
    """Return whole-copy redundancy overhead for `extra_copies` extra
    copies of a `dna_length`-base sequence.

    This is a thin wrapper around Phase 18's
    redundancy_simulation.calculate_storage_overhead() -- the formula
    is defined ONCE there and reused here, never duplicated.
    """
    try:
        result = _copy_redundancy_overhead(dna_length, extra_copies)
    except RedundancySimulationError as exc:
        raise CapacityAnalysisError(str(exc)) from exc
    return {**result, "category": "theoretical"}


# --- 9. Error-correction / coding overhead (Phase 6 checksum, reused) -------------

def calculate_error_correction_overhead(dna_length: int, block_size: int, redundancy_size: int) -> dict:
    """Return Phase 6's checksum-based error-correction overhead for a
    `dna_length`-base sequence, given `block_size`/`redundancy_size`.

    This is a thin wrapper around storage_analysis.calculate_redundancy_
    overhead() (which mirrors dna_error_correction.add_redundancy()'s
    own math) -- reused, not duplicated. This is a DIFFERENT technique
    from calculate_copy_redundancy_overhead() above: a small checksum
    added to blocks of ONE sequence, not multiple whole copies. Exact
    error-correction *success* overhead (how much redundancy is
    actually "used up" recovering real errors) depends on how many
    errors actually occur, which is configuration/scenario-dependent --
    this function only reports the STORAGE overhead of adding the
    checksums, never a success-rate guarantee.
    """
    try:
        result = _error_correction_overhead(dna_length, block_size, redundancy_size)
    except StorageAnalysisError as exc:
        raise CapacityAnalysisError(str(exc)) from exc
    return {**result, "category": "theoretical"}


# --- 7. Optional physical DNA density model (estimated) ---------------------------

def estimate_dna_mass(
    num_bases,
    copies: int = 1,
    average_base_weight_daltons: float = DEFAULT_AVERAGE_BASE_WEIGHT_DALTONS,
) -> dict:
    """Return an ESTIMATED physical mass for `num_bases` DNA bases,
    stored in `copies` copies, using a documented approximate average
    molecular weight per base (`average_base_weight_daltons`).

    This is an educational order-of-magnitude model ONLY:
    - `average_base_weight_daltons` is a user-adjustable ASSUMPTION
      (a commonly cited approximate figure, not a measured constant --
      real average weight varies by base identity, strand form, and
      buffer/salt conditions).
    - The result does NOT account for synthesis, purification,
      sequencing, packaging, or any other real laboratory process or
      loss.
    - It is never presented as an experimentally measured mass.
    """
    _validate_non_negative_number(num_bases, "num_bases")
    if isinstance(copies, bool) or not isinstance(copies, int) or copies < 1:
        raise CapacityAnalysisError("copies must be a whole number of 1 or more.")
    if not isinstance(average_base_weight_daltons, (int, float)) or isinstance(average_base_weight_daltons, bool) or average_base_weight_daltons <= 0:
        raise CapacityAnalysisError("average_base_weight_daltons must be a positive number.")

    total_bases = num_bases * copies
    mass_grams = total_bases * average_base_weight_daltons * DALTON_TO_GRAMS

    return {
        "num_bases": num_bases,
        "copies": copies,
        "total_bases": total_bases,
        "average_base_weight_daltons": average_base_weight_daltons,
        "estimated_mass_grams": mass_grams,
        "estimated_mass_micrograms": mass_grams * 1_000_000,
        "estimated_mass_nanograms": mass_grams * 1_000_000_000,
        "category": "estimated",
        "assumptions": [
            f"Average molecular weight per base assumed to be {average_base_weight_daltons} Da "
            "(a commonly cited approximate figure, not a precise measured constant).",
            "Does not account for synthesis, purification, sequencing, packaging, "
            "or any other real laboratory process or loss.",
        ],
    }


# --- 10. Conventional digital storage comparison (theoretical/illustrative) -------

def compare_to_conventional_storage(sizes_bytes: dict = None) -> list:
    """Return a table comparing illustrative conventional-storage sizes
    against the theoretical DNA bases that would represent the same
    digital size.

    Uses only illustrative, clearly-labeled example sizes (never live
    commercial prices or specs) -- see CONVENTIONAL_STORAGE_EXAMPLES_BYTES.
    No technology is ranked; the table only reports the math.
    """
    sizes_bytes = sizes_bytes if sizes_bytes is not None else CONVENTIONAL_STORAGE_EXAMPLES_BYTES
    rows = []
    for label, num_bytes in sizes_bytes.items():
        rows.append(
            {
                "label": label,
                "digital_size_bytes": num_bytes,
                "theoretical_dna_bases": dna_bases_required_for_bytes(num_bytes),
                "category": "theoretical",
            }
        )
    return rows


# --- 11. Cost estimation model (illustrative, user-supplied assumptions) ---------

def estimate_cost(
    num_bases,
    cost_per_million_bases_synthesis: float = 0.0,
    cost_per_million_bases_sequencing: float = 0.0,
    other_cost: float = 0.0,
) -> dict:
    """Return an ILLUSTRATIVE cost estimate for storing `num_bases` DNA
    bases, using user-supplied per-million-base cost assumptions.

    This NEVER represents a current market quote -- every cost input
    is either a user-provided assumption or a clearly documented
    example value. The calculation itself (synthesis + sequencing +
    other = total) is fully transparent and shown component-by-component.
    """
    _validate_non_negative_number(num_bases, "num_bases")
    for value, name in (
        (cost_per_million_bases_synthesis, "cost_per_million_bases_synthesis"),
        (cost_per_million_bases_sequencing, "cost_per_million_bases_sequencing"),
        (other_cost, "other_cost"),
    ):
        _validate_non_negative_number(value, name)

    millions_of_bases = num_bases / 1_000_000
    synthesis_cost = millions_of_bases * cost_per_million_bases_synthesis
    sequencing_cost = millions_of_bases * cost_per_million_bases_sequencing
    total_cost = synthesis_cost + sequencing_cost + other_cost

    return {
        "num_bases": num_bases,
        "millions_of_bases": round(millions_of_bases, 6),
        "cost_per_million_bases_synthesis": cost_per_million_bases_synthesis,
        "cost_per_million_bases_sequencing": cost_per_million_bases_sequencing,
        "other_cost": other_cost,
        "estimated_synthesis_cost": round(synthesis_cost, 2),
        "estimated_sequencing_cost": round(sequencing_cost, 2),
        "estimated_other_cost": round(other_cost, 2),
        "total_illustrative_cost": round(total_cost, 2),
        "category": "estimated",
        "disclaimer": "Illustrative estimate based on user-provided assumptions -- not a current market quote.",
    }


# --- 12. Scale examples (theoretical, math only -- no giant strings) -------------

def generate_scale_examples(extra_copies: int = 0, sizes_bytes: dict = None) -> list:
    """Return theoretical DNA-length figures for illustrative file/data
    sizes (1 MB / 1 GB / 1 TB / 1 PB by default), including the
    redundancy-adjusted total for `extra_copies` extra whole copies.

    PERFORMANCE SAFETY: this only performs integer/float arithmetic --
    it never allocates a DNA string of any of these sizes, so a "1 PB"
    example costs the same, tiny amount of memory as a "1 MB" example.
    """
    sizes_bytes = sizes_bytes if sizes_bytes is not None else SCALE_EXAMPLES_BYTES
    rows = []
    for label, num_bytes in sizes_bytes.items():
        theoretical_bases = int(dna_bases_required_for_bytes(num_bytes))
        redundancy = calculate_copy_redundancy_overhead(theoretical_bases, extra_copies)
        rows.append(
            {
                "label": label,
                "digital_size_bytes": num_bytes,
                "theoretical_dna_bases": theoretical_bases,
                "extra_copies": extra_copies,
                "redundancy_adjusted_bases": redundancy["total_dna_length"],
                "redundancy_overhead_percent": redundancy["overhead_percent"],
                "category": "theoretical",
            }
        )
    return rows
