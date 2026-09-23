"""
DNA data integrity, validation, and corruption-detection logic
(non-UI, no Streamlit dependency).

This module never changes the real encoding/decoding pipeline
(dna_encoder.py / dna_decoder.py) -- it only INSPECTS a DNA sequence
(and, optionally, the original file bytes it should decode back into)
and reports what it finds, using clear, honest categories. It reuses
the existing GC-content / homopolymer analysis from encoding_models.py
and the existing decoder/comparison functions from dna_decoder.py
rather than duplicating that logic.

STATUS CATEGORIES
------------------
Every integrity report resolves to exactly one of these statuses:

- "invalid"           : the sequence is empty, or contains characters
                        other than A/T/G/C. Cannot be decoded at all.
- "incomplete"        : only valid bases, but the length is not a
                        multiple of 4 (BASES_PER_BYTE) -- it cannot be
                        split into whole bytes without guessing. This
                        is the classic sign of an insertion/deletion.
- "corrupted"         : the sequence decodes without error, but either
                        (a) it was compared against known original
                        bytes and they do NOT match, or (b) decoding
                        itself failed unexpectedly despite passing the
                        basic checks.
- "unable_to_verify"  : the sequence decodes fine, but there is no
                        original file/bytes available to compare it
                        against, so whether it matches "the original"
                        cannot be determined either way.
- "valid"             : the sequence decodes fine and no recovery
                        confirmation was ever requested (a pure
                        structural check, not a claim about matching
                        any particular original file).
- "recovered"         : the sequence decodes AND was compared against
                        known original bytes AND they are identical.
                        This is the ONLY status that ever implies
                        successful, confirmed recovery.

Warnings (unusual GC content, long homopolymer runs, an unexpected
length when a specific expected length was given) are never treated as
proof of corruption by themselves -- they are risk indicators, kept
separate from "errors" (which do affect the final status).
"""

from app.modules.dna_encoder import BITS_TO_BASE, BITS_PER_BASE
from app.modules.dna_decoder import (
    BITS_PER_BYTE,
    DNADecodingError,
    decode_dna_to_file,
    compare_bytes as _compare_bytes_basic,
)
from app.modules.encoding_models import (
    DEFAULT_HOMOPOLYMER_THRESHOLD,
    analyze_gc_content,
    count_homopolymer_runs,
)
from app.modules.file_handler import compute_content_hash

VALID_BASES = tuple(BITS_TO_BASE.values())  # ("A", "C", "G", "T")
VALID_BASES_SET = set(VALID_BASES)

# 8 bits per byte / 2 bits per base = 4 bases per byte. A DNA length
# that isn't a multiple of this can never split evenly into whole
# bytes -- this is the same arithmetic dna_decoder.py relies on.
BASES_PER_BYTE = BITS_PER_BYTE // BITS_PER_BASE

# GC-percentage band outside of which a warning (never an error) is
# raised. This is a rough, commonly-cited comfort zone for real DNA
# synthesis/sequencing -- not a hard pass/fail rule.
GC_WARNING_LOW_PERCENT = 20.0
GC_WARNING_HIGH_PERCENT = 80.0

STATUS_INVALID = "invalid"
STATUS_INCOMPLETE = "incomplete"
STATUS_CORRUPTED = "corrupted"
STATUS_UNABLE_TO_VERIFY = "unable_to_verify"
STATUS_VALID = "valid"
STATUS_RECOVERED = "recovered"

ALL_STATUSES = (
    STATUS_INVALID,
    STATUS_INCOMPLETE,
    STATUS_CORRUPTED,
    STATUS_UNABLE_TO_VERIFY,
    STATUS_VALID,
    STATUS_RECOVERED,
)


class DNAIntegrityError(Exception):
    """Raised when integrity-check inputs themselves are the wrong type."""


# --- A. DNA character validation ----------------------------------------------

def check_dna_characters(sequence: str) -> dict:
    """Tolerant character-validity check -- never raises, even for
    empty or invalid input, since this is a read-only diagnostic (not
    part of the strict encode/decode pipeline).

    Lowercase is accepted and normalized to uppercase, consistent with
    every other DNA-validation function in BioVault (case carries no
    information in this scheme).
    """
    if not isinstance(sequence, str):
        raise DNAIntegrityError("sequence must be a string.")

    normalized = sequence.upper()
    invalid_characters = sorted(set(normalized) - VALID_BASES_SET)
    invalid_character_count = sum(1 for char in normalized if char not in VALID_BASES_SET)

    return {
        "dna_length": len(normalized),
        "is_empty": len(normalized) == 0,
        "invalid_characters": invalid_characters,
        "invalid_character_count": invalid_character_count,
        "is_valid": len(normalized) > 0 and invalid_character_count == 0,
    }


# --- B. DNA length validation --------------------------------------------------

def check_dna_length(dna_length: int) -> dict:
    """Check whether `dna_length` (in bases) is compatible with the
    existing 2-bit-per-base encoding: every 4 bases represent exactly
    one byte, with no padding ever used (see dna_encoder.py), so any
    other length cannot be split into whole bytes.
    """
    if isinstance(dna_length, bool) or not isinstance(dna_length, int) or dna_length < 0:
        raise DNAIntegrityError("dna_length must be a non-negative whole number.")

    remainder_bases = dna_length % BASES_PER_BYTE
    is_length_compatible = remainder_bases == 0

    return {
        "dna_length": dna_length,
        "bases_per_byte": BASES_PER_BYTE,
        "is_length_compatible": is_length_compatible,
        "remainder_bases": remainder_bases,
        "expected_byte_count": (dna_length // BASES_PER_BYTE) if is_length_compatible else None,
    }


# --- C. DNA statistics ----------------------------------------------------------

def calculate_dna_statistics(sequence: str) -> dict:
    """Return full base-composition statistics for `sequence`.

    Reuses encoding_models.analyze_gc_content() rather than
    duplicating counting/GC/homopolymer logic -- this module only adds
    the integrity-specific interpretation (warnings/errors/status) on
    top of those existing, already-tested statistics.
    """
    if not isinstance(sequence, str):
        raise DNAIntegrityError("sequence must be a string.")
    return analyze_gc_content(sequence)


# --- D. DNA corruption analysis (warnings/errors, no final status) ------------

def analyze_corruption(
    sequence: str,
    expected_dna_length: int = None,
    homopolymer_threshold: int = DEFAULT_HOMOPOLYMER_THRESHOLD,
) -> dict:
    """Look for possible integrity problems in `sequence` and return
    them split into `errors` (things that make the data unusable as-is)
    and `warnings` (risk indicators that do NOT by themselves prove
    corruption). Never raises for bad DNA content -- that IS what this
    function reports on.
    """
    if not isinstance(sequence, str):
        raise DNAIntegrityError("sequence must be a string.")

    errors = []
    warnings = []

    char_check = check_dna_characters(sequence)
    length_check = check_dna_length(char_check["dna_length"])

    if char_check["is_empty"]:
        errors.append("The DNA sequence is empty -- there is nothing to validate or decode.")
    elif char_check["invalid_character_count"] > 0:
        errors.append(
            f"Found {char_check['invalid_character_count']} invalid character(s): "
            f"{', '.join(repr(c) for c in char_check['invalid_characters'])}. "
            "Only A, T, G, C (any case) are valid DNA bases."
        )

    if not char_check["is_empty"] and not length_check["is_length_compatible"]:
        errors.append(
            f"DNA length ({length_check['dna_length']} bases) is not a multiple of "
            f"{BASES_PER_BYTE} -- it cannot be split into whole bytes without "
            "guessing. This usually indicates one or more bases were inserted or "
            "deleted."
        )

    if expected_dna_length is not None and char_check["dna_length"] != expected_dna_length:
        warnings.append(
            f"DNA length ({char_check['dna_length']} bases) does not match the "
            f"expected length ({expected_dna_length} bases) -- a possible sign of "
            "an insertion or deletion."
        )

    if not char_check["is_empty"] and char_check["invalid_character_count"] == 0:
        stats = calculate_dna_statistics(sequence)
        if stats["gc_percentage"] < GC_WARNING_LOW_PERCENT or stats["gc_percentage"] > GC_WARNING_HIGH_PERCENT:
            direction = "low" if stats["gc_percentage"] < GC_WARNING_LOW_PERCENT else "high"
            warnings.append(
                f"GC content is unusually {direction} ({stats['gc_percentage']}%). "
                "This is a risk indicator, not proof of corruption -- some "
                "legitimate data can still encode to skewed GC content."
            )

        homopolymer = count_homopolymer_runs(sequence, homopolymer_threshold)
        if homopolymer["runs_at_or_above_threshold"] > 0:
            warnings.append(
                f"Found {homopolymer['runs_at_or_above_threshold']} homopolymer "
                f"run(s) of {homopolymer_threshold}+ identical bases in a row "
                f"(longest: {homopolymer['longest_run']}). Long runs are a known "
                "risk factor for real DNA sequencing errors, not proof that this "
                "specific sequence is corrupted."
            )

    return {
        "errors": errors,
        "warnings": warnings,
        "char_check": char_check,
        "length_check": length_check,
    }


# --- E. Original-versus-recovered comparison ------------------------------------

def compare_original_and_recovered(original_bytes: bytes, recovered_bytes: bytes) -> dict:
    """Safely compare original and recovered bytes: identity, sizes,
    the first differing byte position (if any), the total number of
    differing bytes, and a SHA-256 hash of each side.

    Reuses dna_decoder.compare_bytes() for the core identical/size/
    differing-byte-count logic (never re-implementing that check), and
    adds the first-difference index and hashes on top. Only a compact
    hash of each side is returned -- never the raw file content.
    """
    if not isinstance(original_bytes, (bytes, bytearray)) or not isinstance(recovered_bytes, (bytes, bytearray)):
        raise DNAIntegrityError("original_bytes and recovered_bytes must both be bytes.")

    original_bytes = bytes(original_bytes)
    recovered_bytes = bytes(recovered_bytes)
    basic = _compare_bytes_basic(original_bytes, recovered_bytes)

    first_difference_index = None
    shorter_length = min(len(original_bytes), len(recovered_bytes))
    for i in range(shorter_length):
        if original_bytes[i] != recovered_bytes[i]:
            first_difference_index = i
            break
    if first_difference_index is None and len(original_bytes) != len(recovered_bytes):
        first_difference_index = shorter_length  # first byte past the shorter side

    return {
        "is_identical": basic["is_identical"],
        "original_length": basic["original_size_bytes"],
        "recovered_length": basic["recovered_size_bytes"],
        "first_difference_index": first_difference_index,
        "differing_byte_count": basic["differing_bytes"],
        "original_hash": compute_content_hash(original_bytes),
        "recovered_hash": compute_content_hash(recovered_bytes),
    }


# --- F. Integrity report (the single entry point the UI should use) ------------

def build_integrity_report(
    dna_sequence: str,
    original_bytes: bytes = None,
    expected_dna_length: int = None,
    homopolymer_threshold: int = DEFAULT_HOMOPOLYMER_THRESHOLD,
    expects_recovery_check: bool = True,
) -> dict:
    """Build one structured integrity report for `dna_sequence`.

    - If `original_bytes` is given, decoding is attempted and the
      result is compared against it -- the report's status becomes
      "recovered" only if they are byte-for-byte identical, or
      "corrupted" if they differ.
    - If `original_bytes` is None and `expects_recovery_check` is True
      (the default -- appropriate whenever the caller's intent is to
      confirm a specific file was recovered), the status becomes
      "unable_to_verify": the sequence may decode fine, but nothing
      confirms it matches any particular original.
    - If `original_bytes` is None and `expects_recovery_check` is
      False (a pure structural check, no recovery claim intended), the
      status becomes "valid" when the sequence decodes successfully.

    Never raises for bad DNA content -- that is exactly what this
    report describes, via `status`/`errors`/`warnings`.
    """
    if not isinstance(dna_sequence, str):
        raise DNAIntegrityError("dna_sequence must be a string.")

    corruption = analyze_corruption(dna_sequence, expected_dna_length, homopolymer_threshold)
    char_check = corruption["char_check"]
    length_check = corruption["length_check"]
    errors = list(corruption["errors"])
    warnings = list(corruption["warnings"])

    can_decode = False
    comparison_result = None
    recovery_confirmed = None
    original_hash = compute_content_hash(original_bytes) if original_bytes is not None else None
    recovered_hash = None

    if char_check["is_empty"]:
        status = STATUS_INVALID
    elif char_check["invalid_character_count"] > 0:
        status = STATUS_INVALID
    elif not length_check["is_length_compatible"]:
        status = STATUS_INCOMPLETE
    else:
        try:
            decoded = decode_dna_to_file(dna_sequence)
            can_decode = True
        except DNADecodingError as exc:
            errors.append(f"Decoding failed unexpectedly: {exc}")
            status = STATUS_CORRUPTED
        else:
            recovered_hash = compute_content_hash(decoded["recovered_bytes"])
            if original_bytes is not None:
                comparison_result = compare_original_and_recovered(original_bytes, decoded["recovered_bytes"])
                recovery_confirmed = comparison_result["is_identical"]
                if recovery_confirmed:
                    status = STATUS_RECOVERED
                else:
                    status = STATUS_CORRUPTED
                    errors.append(
                        f"Recovered data does not match the original file: "
                        f"{comparison_result['differing_byte_count']:,} byte(s) differ."
                    )
            elif expects_recovery_check:
                status = STATUS_UNABLE_TO_VERIFY
            else:
                status = STATUS_VALID

    is_valid = status in (STATUS_VALID, STATUS_RECOVERED)
    is_corrupted = status == STATUS_CORRUPTED
    is_complete = (not char_check["is_empty"]) and length_check["is_length_compatible"]

    return {
        "status": status,
        "is_valid": is_valid,
        "is_corrupted": is_corrupted,
        "is_complete": is_complete,
        "can_decode": can_decode,
        "recovery_confirmed": recovery_confirmed,
        "warnings": warnings,
        "errors": errors,
        "dna_length": char_check["dna_length"],
        "invalid_character_count": char_check["invalid_character_count"],
        "original_hash": original_hash,
        "recovered_hash": recovered_hash,
        "comparison_result": comparison_result,
    }
