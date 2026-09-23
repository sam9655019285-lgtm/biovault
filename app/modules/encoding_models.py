"""
Educational DNA-encoding-model comparison logic (non-UI, no Streamlit
dependency).

BioVault's real file-storage pipeline uses exactly ONE encoding scheme:
the fixed, reversible 2-bit mapping in dna_encoder.py / dna_decoder.py
(reused here as "Model A"). Nothing in this module changes that
pipeline, and nothing in the normal upload -> encode -> decode -> export
flow ever calls into this module. It exists purely so a user can
COMPARE that real scheme against a few clearly labeled educational
alternatives that illustrate tradeoffs real DNA-storage research cares
about (GC balance, homopolymer runs) -- without pretending any
simulated model here is a laboratory-ready encoding algorithm.

Every result this module returns states explicitly whether it is:

- REVERSIBLE ("model_category": "reversible"): the exact original bytes
  can be recovered from it using BioVault's existing, unmodified
  decoder (dna_decoder.decode_dna_to_file). Only Model A qualifies.
- ANALYSIS-ONLY ("model_category": "analysis-only"): it measures or
  simulates something about a sequence but produces no alternate
  encoding meant to be decoded back into a file. Models B, C, and D are
  all analysis-only -- Model B's "balanced" sequence is a demonstration
  only and is never passed to the decoder anywhere in this app.

No value here is ever fabricated: every number comes from actually
running the stated calculation against the actual input.
"""

from itertools import groupby

from app.modules.dna_encoder import BITS_TO_BASE, bytes_to_binary, encode_file_to_dna
from app.modules.dna_decoder import decode_dna_to_file, compare_bytes

VALID_BASES = tuple(BITS_TO_BASE.values())  # ("A", "C", "G", "T")
VALID_BASES_SET = set(VALID_BASES)
GC_BASES = {"G", "C"}

# Model B's second candidate mapping table: a different (but equally
# valid, equally reversible-in-isolation) 2-bit -> base assignment than
# the real encoder's BITS_TO_BASE. Having a genuinely DIFFERENT mapping
# -- not just a complement of BITS_TO_BASE's output -- is essential:
# complementing a base (A<->T, C<->G) never changes whether it counts
# as GC or AT, so it could never actually shift GC content. This second
# table deliberately assigns some bit patterns to the opposite GC/AT
# family from BITS_TO_BASE, so choosing between the two tables per
# block can meaningfully move a block's GC percentage.
GC_BALANCED_ALT_TABLE = {"00": "G", "01": "T", "10": "C", "11": "A"}

DEFAULT_HOMOPOLYMER_THRESHOLD = 4
DEFAULT_GC_BLOCK_SIZE = 4

MODEL_IDS = ("A", "B", "C", "D")


class EncodingModelError(Exception):
    """Raised when encoding-model inputs are invalid."""


def validate_dna_sequence(sequence: str) -> str:
    """Validate a DNA sequence and return it normalized to uppercase.

    Same strict rules used throughout BioVault: non-empty, only
    A/T/G/C (any case, normalized to uppercase). Used by Model A/B/C,
    which all operate on an already-valid, already-encoded sequence.
    Model D's analysis function is intentionally more tolerant (see
    analyze_gc_content) since reporting invalid-character counts is
    part of its job.
    """
    if not isinstance(sequence, str):
        raise EncodingModelError("DNA sequence must be a string.")
    if len(sequence) == 0:
        raise EncodingModelError("DNA sequence is empty -- nothing to analyze.")

    normalized = sequence.upper()
    invalid_chars = sorted(set(normalized) - VALID_BASES_SET)
    if invalid_chars:
        raise EncodingModelError(
            "DNA sequence contains invalid character(s): "
            f"{', '.join(repr(c) for c in invalid_chars)}. "
            "Only A, T, G, C (any case) are allowed."
        )
    return normalized


def _base_runs(sequence: str):
    """Yield (character, run_length) for each maximal consecutive run
    of the same character in `sequence`. Works on ANY string (including
    one with invalid characters), since Model D must be able to report
    on imperfect input without crashing."""
    for char, group in groupby(sequence):
        yield char, sum(1 for _ in group)


def longest_homopolymer_run(sequence: str) -> int:
    """Return the length of the longest run of one valid base (A, T, G,
    or C) repeated consecutively. Non-base characters never contribute
    to a run and never extend one. Returns 0 for an empty sequence."""
    if not isinstance(sequence, str):
        raise EncodingModelError("sequence must be a string.")

    normalized = sequence.upper()
    valid_run_lengths = [length for char, length in _base_runs(normalized) if char in VALID_BASES_SET]
    return max(valid_run_lengths, default=0)


def count_homopolymer_runs(sequence: str, threshold: int = DEFAULT_HOMOPOLYMER_THRESHOLD) -> dict:
    """Return homopolymer statistics for `sequence`: every maximal run
    of a single valid base, the longest one, and how many runs meet or
    exceed `threshold` bases in length.

    A `threshold`-base-or-longer run is flagged because real DNA
    synthesis/sequencing hardware can lose count of exactly how many
    identical bases occurred in a row once a run gets long -- this is
    explained in the model's "explanation" text, not asserted here.
    """
    if not isinstance(sequence, str):
        raise EncodingModelError("sequence must be a string.")
    if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
        raise EncodingModelError("threshold must be a positive whole number.")

    normalized = sequence.upper()
    runs = [(char, length) for char, length in _base_runs(normalized) if char in VALID_BASES_SET]
    matching_runs = [run for run in runs if run[1] >= threshold]
    longest_run = max((length for _, length in runs), default=0)

    return {
        "threshold": threshold,
        "longest_run": longest_run,
        "runs_at_or_above_threshold": len(matching_runs),
        "matching_runs": matching_runs,
    }


def analyze_gc_content(sequence: str) -> dict:
    """Return full base-composition statistics for `sequence`.

    Unlike validate_dna_sequence(), this NEVER raises for invalid
    characters or empty input -- it is a read-only statistics function
    (Model D), so it reports what it finds (including an invalid-
    character count and a 0%/0-length result for empty input) instead
    of refusing to analyze imperfect data.
    """
    if not isinstance(sequence, str):
        raise EncodingModelError("sequence must be a string.")

    normalized = sequence.upper()
    counts = {base: 0 for base in VALID_BASES}
    invalid_count = 0
    for char in normalized:
        if char in VALID_BASES_SET:
            counts[char] += 1
        else:
            invalid_count += 1

    valid_base_count = sum(counts.values())
    gc_count = counts["G"] + counts["C"]
    at_count = counts["A"] + counts["T"]

    return {
        "total_length": len(normalized),
        "valid_base_count": valid_base_count,
        "counts": counts,
        "gc_count": gc_count,
        "at_count": at_count,
        "gc_percentage": round((gc_count / valid_base_count) * 100, 2) if valid_base_count else 0.0,
        "at_percentage": round((at_count / valid_base_count) * 100, 2) if valid_base_count else 0.0,
        "longest_homopolymer_run": longest_homopolymer_run(normalized),
        "invalid_character_count": invalid_count,
    }


# --- Model A: Basic Binary-to-DNA (existing/default, reversible) -------------

def model_a_basic_binary(data: bytes) -> dict:
    """Run BioVault's real, default, reversible encoding (Model A).

    This does not add any new encoding logic -- it calls the exact same
    dna_encoder.encode_file_to_dna() / dna_decoder.decode_dna_to_file()
    functions used everywhere else in the app, then confirms round-trip
    recovery, so the comparison table's "reversible" claim for this row
    is always actually verified, never assumed.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise EncodingModelError("data must be bytes.")

    encoding_result = encode_file_to_dna(data)
    dna_sequence = encoding_result["dna_sequence"]

    if dna_sequence:
        decoded = decode_dna_to_file(dna_sequence)
        comparison = compare_bytes(data, decoded["recovered_bytes"])
        recovery_confirmed = comparison["is_identical"]
    else:
        recovery_confirmed = len(data) == 0  # empty in, empty out is correct

    gc_stats = analyze_gc_content(dna_sequence) if dna_sequence else analyze_gc_content("")
    homopolymer_stats = (
        count_homopolymer_runs(dna_sequence)
        if dna_sequence
        else {"threshold": DEFAULT_HOMOPOLYMER_THRESHOLD, "longest_run": 0, "runs_at_or_above_threshold": 0, "matching_runs": []}
    )

    return {
        "model_name": "Model A - Basic Binary-to-DNA (default)",
        "model_category": "reversible",
        "reversible": True,
        "original_input_size_bytes": len(data),
        "dna_sequence": dna_sequence,
        "dna_length": len(dna_sequence),
        "storage_size_estimate_bases": len(dna_sequence),
        "storage_size_is_estimate": False,
        "gc_percentage": gc_stats["gc_percentage"],
        "at_percentage": gc_stats["at_percentage"],
        "gc_count": gc_stats["gc_count"],
        "invalid_character_count": gc_stats["invalid_character_count"],
        "longest_homopolymer_run": gc_stats["longest_homopolymer_run"],
        "homopolymer_stats": homopolymer_stats,
        "recovery_confirmed": recovery_confirmed,
        "warnings": [],
        "explanation": (
            "This is BioVault's actual default encoding: 00->A, 01->C, "
            "10->G, 11->T. It is fully reversible -- decoding it "
            "recovers the exact original bytes -- and is the scheme "
            "used everywhere else in the app for real encoding/decoding."
        ),
    }


# --- Model B: GC-balanced simulated model (analysis-only, NOT reversible) ----

def model_b_gc_balanced_simulation(data: bytes, block_size_bases: int = DEFAULT_GC_BLOCK_SIZE) -> dict:
    """Simulate one simple GC-balancing strategy over the same binary
    data Model A encodes, for educational comparison only.

    For each block of `block_size_bases` bases' worth of bits, this
    picks whichever of two DIFFERENT valid 2-bit -> base mappings
    (BITS_TO_BASE, the real encoder's table, or GC_BALANCED_ALT_TABLE,
    a second candidate table) keeps the running GC percentage closer to
    a 50% target for that same underlying bit content, and keeps that
    choice.

    THIS IS A SIMULATED, EDUCATIONAL DEMONSTRATION -- NOT A PRODUCTION-
    READY BIOLOGICAL ENCODING ALGORITHM, AND NOT REVERSIBLE AS
    IMPLEMENTED HERE. A real, working version of this idea would need
    to also store, for every block, which of the two tables was used
    (extra "side channel" data), so the exact original bytes could be
    recovered later. This simplified teaching version deliberately
    leaves that bookkeeping out to keep the demonstration simple, so
    the resulting sequence below must never be passed to BioVault's
    decoder or treated as recoverable -- it exists only to show what a
    GC-balancing choice *could* achieve, not to actually achieve it.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise EncodingModelError("data must be bytes.")
    if isinstance(block_size_bases, bool) or not isinstance(block_size_bases, int) or block_size_bases < 1:
        raise EncodingModelError("block_size_bases must be a positive whole number.")

    binary_str = bytes_to_binary(data)
    chunk_bits = block_size_bases * 2  # 2 bits per base

    simulated_parts = []
    running_gc = 0
    running_total = 0

    for i in range(0, len(binary_str), chunk_bits):
        bit_chunk = binary_str[i : i + chunk_bits]
        default_block = "".join(BITS_TO_BASE[bit_chunk[j : j + 2]] for j in range(0, len(bit_chunk), 2))
        alt_block = "".join(GC_BALANCED_ALT_TABLE[bit_chunk[j : j + 2]] for j in range(0, len(bit_chunk), 2))

        default_gc = sum(1 for base in default_block if base in GC_BASES)
        alt_gc = sum(1 for base in alt_block if base in GC_BASES)

        projected_total = running_total + len(default_block)
        target = projected_total / 2
        projected_with_default = running_gc + default_gc
        projected_with_alt = running_gc + alt_gc

        if abs(projected_with_default - target) <= abs(projected_with_alt - target):
            chosen_block = default_block
            running_gc = projected_with_default
        else:
            chosen_block = alt_block
            running_gc = projected_with_alt

        running_total = projected_total
        simulated_parts.append(chosen_block)

    simulated_sequence = "".join(simulated_parts)
    original_stats = analyze_gc_content(encode_file_to_dna(data)["dna_sequence"]) if data else analyze_gc_content("")
    simulated_stats = analyze_gc_content(simulated_sequence) if simulated_sequence else analyze_gc_content("")

    return {
        "model_name": "Model B - GC-Balanced (simulated)",
        "model_category": "analysis-only",
        "reversible": False,
        "dna_sequence": simulated_sequence,
        "dna_length": simulated_stats["total_length"],
        "storage_size_estimate_bases": simulated_stats["total_length"],
        "storage_size_is_estimate": True,
        "gc_percentage": simulated_stats["gc_percentage"],
        "at_percentage": simulated_stats["at_percentage"],
        "gc_count": simulated_stats["gc_count"],
        "invalid_character_count": simulated_stats["invalid_character_count"],
        "longest_homopolymer_run": simulated_stats["longest_homopolymer_run"],
        "homopolymer_stats": count_homopolymer_runs(simulated_sequence) if simulated_sequence else None,
        "original_gc_percentage": original_stats["gc_percentage"],
        "recovery_confirmed": None,  # not applicable -- this model is not reversible
        "warnings": [
            "SIMULATED / ANALYSIS-ONLY: this sequence is a demonstration "
            "of GC-balancing only. The information needed to reverse it "
            "(which per-block choice was made) is not stored, so it "
            "CANNOT be decoded back into the original file.",
        ],
        "explanation": (
            "This model shows what choosing between a block and its "
            "base-complement (A<->T, C<->G), block by block, could do to "
            "even out GC content -- a real goal in DNA-storage research, "
            "since very high or very low GC content can make DNA harder "
            "to synthesize and sequence reliably. It is not a working "
            "encoder: BioVault does not store the per-block choice, so "
            "this demonstration sequence is not reversible."
        ),
    }


# --- Model C: Homopolymer-limited simulated model (analysis-only) -----------

def model_c_homopolymer_analysis(dna_sequence: str, threshold: int = DEFAULT_HOMOPOLYMER_THRESHOLD) -> dict:
    """Analyze homopolymer (repeated-base) runs in an already-encoded
    Model A DNA sequence.

    This model does not transform the sequence at all -- it only
    measures it -- so it is analysis-only by nature rather than by a
    reversibility limitation: there is nothing here to "reverse"
    because the underlying, still fully-reversible Model A sequence is
    never modified.
    """
    normalized = validate_dna_sequence(dna_sequence)
    run_stats = count_homopolymer_runs(normalized, threshold)
    gc_stats = analyze_gc_content(normalized)

    warnings = []
    if run_stats["runs_at_or_above_threshold"] > 0:
        warnings.append(
            f"Found {run_stats['runs_at_or_above_threshold']} run(s) of "
            f"{threshold}+ identical bases in a row (longest: "
            f"{run_stats['longest_run']} bases). Long repeated runs like "
            "'AAAA' or 'GGGG' are harder for real DNA sequencing/synthesis "
            "hardware to count exactly, which can introduce errors."
        )

    return {
        "model_name": "Model C - Homopolymer Analysis",
        "model_category": "analysis-only",
        "reversible": True,  # analysis only; the underlying sequence is untouched
        "dna_sequence": normalized,
        "dna_length": len(normalized),
        "storage_size_estimate_bases": len(normalized),
        "storage_size_is_estimate": False,
        "gc_percentage": gc_stats["gc_percentage"],
        "at_percentage": gc_stats["at_percentage"],
        "gc_count": gc_stats["gc_count"],
        "invalid_character_count": gc_stats["invalid_character_count"],
        "longest_homopolymer_run": run_stats["longest_run"],
        "homopolymer_stats": run_stats,
        "recovery_confirmed": None,  # this model doesn't decode anything itself
        "warnings": warnings,
        "explanation": (
            "This model measures 'homopolymer runs' -- the same DNA base "
            "repeated several times in a row (e.g. 'AAAA'). It does not "
            "change the sequence, only reports on it: the longest run "
            "found, and how many runs are at or above the chosen "
            "threshold. BioVault's own error-correction method (Phase 6) "
            "does not specifically target this kind of risk."
        ),
    }


# --- Model D: GC-content analysis (pure analysis-only) -----------------------

def model_d_gc_content_analysis(dna_sequence: str) -> dict:
    """Return pure base-composition/GC statistics for an already-encoded
    Model A DNA sequence, as a standalone comparison-table row."""
    normalized = validate_dna_sequence(dna_sequence)
    stats = analyze_gc_content(normalized)

    return {
        "model_name": "Model D - GC-Content Analysis",
        "model_category": "analysis-only",
        "reversible": True,  # analysis only; the underlying sequence is untouched
        "dna_sequence": normalized,
        "dna_length": stats["total_length"],
        "storage_size_estimate_bases": stats["total_length"],
        "storage_size_is_estimate": False,
        "gc_percentage": stats["gc_percentage"],
        "at_percentage": stats["at_percentage"],
        "gc_count": stats["gc_count"],
        "invalid_character_count": stats["invalid_character_count"],
        "longest_homopolymer_run": stats["longest_homopolymer_run"],
        "homopolymer_stats": count_homopolymer_runs(normalized),
        "base_counts": stats["counts"],
        "recovery_confirmed": None,
        "warnings": [],
        "explanation": (
            "This model does not encode or transform anything -- it "
            "reports base-composition statistics (GC%, AT%, longest "
            "repeated-base run, invalid-character count) for the DNA "
            "sequence already produced by Model A."
        ),
    }


# --- Coordinator: run a selection of models together ------------------------

def run_model_comparison(
    data: bytes,
    selected_models: list = None,
    homopolymer_threshold: int = DEFAULT_HOMOPOLYMER_THRESHOLD,
    gc_block_size: int = DEFAULT_GC_BLOCK_SIZE,
) -> dict:
    """Run every requested model against `data` and return one dict
    keyed by model id ("A", "B", "C", "D"; only the requested ones are
    present). Models B, C, and D all analyze the Model A DNA sequence
    (never a second, separately-encoded copy), since none of them are
    meant to replace it -- they exist to compare against it.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise EncodingModelError("data must be bytes.")

    selected_models = list(selected_models) if selected_models is not None else list(MODEL_IDS)
    unknown = set(selected_models) - set(MODEL_IDS)
    if unknown:
        raise EncodingModelError(f"Unknown model id(s): {', '.join(sorted(unknown))}.")

    results = {}
    model_a_result = model_a_basic_binary(data)
    dna_sequence = model_a_result["dna_sequence"]

    if "A" in selected_models:
        results["A"] = model_a_result

    if "B" in selected_models:
        results["B"] = model_b_gc_balanced_simulation(data, gc_block_size) if data else None

    if "C" in selected_models:
        results["C"] = (
            model_c_homopolymer_analysis(dna_sequence, homopolymer_threshold)
            if dna_sequence
            else None
        )

    if "D" in selected_models:
        results["D"] = model_d_gc_content_analysis(dna_sequence) if dna_sequence else None

    return {
        "input_size_bytes": len(data),
        "models": results,
    }
