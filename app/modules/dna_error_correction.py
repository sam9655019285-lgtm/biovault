"""
DNA error detection & correction logic (non-UI, no Streamlit dependency).

This module adds a small amount of redundancy to a DNA sequence so that
some errors introduced later (e.g. by the Mutation Simulator) can be
*detected*, and in limited, unambiguous cases, *corrected*. It is a
simplified teaching tool, not a research-grade or biologically accurate
error-correcting code.

REDUNDANCY METHOD (block checksum)
-------------------------------------
- BLOCK SIZE: the DNA sequence is split into consecutive blocks of
  `block_size` bases each. The final block may be shorter than
  `block_size` if the sequence length isn't an exact multiple -- this
  is handled explicitly (no padding is ever added to the DNA data).

- CHECKSUM: each base has a numeric value 0-3, using the same 2-bit
  mapping as the encoder (A=0, C=1, G=2, T=3). A block's checksum is
  the sum of its bases' values, taken modulo 4, then re-encoded back
  into a single DNA base using that same mapping. For example, a block
  with checksum value 2 is represented by the base "G".

- REDUNDANCY SIZE: the checksum base is repeated `redundancy_size`
  times and appended immediately after its block, so a "protected"
  sequence looks like:  [block 1][checksum x N][block 2][checksum x N]...
  Repeating the checksum base lets us recover it by majority vote even
  if one of the copies is itself corrupted.

WHAT CAN BE DETECTED
-----------------------
- Any block whose recalculated checksum does not match its stored
  checksum is flagged as containing an error (substitutions in either
  the data block or the redundancy copies can trigger this).
- If the received sequence's total length doesn't match what
  `block_size`/`redundancy_size`/`original_length` predict, that is
  reported as a structural error (a strong sign of insertions or
  deletions), since block boundaries can no longer be trusted.

WHAT CAN BE CORRECTED
-------------------------
- At most ONE substitution error per block can be corrected, and only
  when exactly one single-base edit of the block makes its checksum
  match the stored checksum again. If more than one possible edit
  matches (ambiguous) or none do, the block is reported as detected
  but NOT corrected -- this method never guesses.

WHAT CANNOT BE CORRECTED (IMPORTANT LIMITATIONS)
----------------------------------------------------
- Insertions or deletions anywhere in the sequence break the fixed
  block/redundancy layout entirely; this method can only report a
  structural length mismatch, not locate or fix them.
- Two or more substitution errors within the same block are often
  uncorrectable: the checksum is only 4-valued (mod 4), so with larger
  block sizes it becomes increasingly likely that several different
  single-base edits coincidentally produce a matching checksum, which
  this module treats as ambiguous and refuses to guess. Using a
  smaller block_size reduces this risk (at the cost of more redundancy
  overhead relative to the amount of data protected).
- If every copy of a block's checksum is itself corrupted such that no
  base has a clear majority, the intended checksum cannot be
  determined and the block is reported as uncorrectable.

This is intentionally a transparent, honest educational demonstration
of *why* real DNA data storage systems need much more sophisticated
error-correcting codes than a simple checksum.
"""

from collections import Counter

from app.modules.dna_encoder import BASE_TO_BITS, BITS_TO_BASE

VALID_BASES = tuple(BITS_TO_BASE.values())  # ("A", "C", "G", "T")
VALID_BASES_SET = set(VALID_BASES)

# Base <-> numeric value (0-3), reusing the encoder's 2-bit mapping so
# this module can never disagree with the encoder/decoder about what
# each base "means".
BASE_VALUE = {base: int(bits, 2) for base, bits in BASE_TO_BITS.items()}
VALUE_TO_BASE = {value: base for base, value in BASE_VALUE.items()}

DEFAULT_BLOCK_SIZE = 4
DEFAULT_REDUNDANCY_SIZE = 2
MAX_BLOCK_SIZE = 200
MAX_REDUNDANCY_SIZE = 20


class DNAErrorCorrectionError(Exception):
    """Raised when DNA data, a block size, or a redundancy size is invalid."""


def validate_dna_sequence(sequence: str) -> str:
    """Validate a DNA sequence and return it normalized to uppercase.

    Same rules used throughout BioVault: non-empty, only A/T/G/C (any
    case, normalized to uppercase). Invalid characters are rejected,
    never silently stripped or repaired.
    """
    if not isinstance(sequence, str):
        raise DNAErrorCorrectionError("DNA sequence must be a string.")

    if len(sequence) == 0:
        raise DNAErrorCorrectionError("DNA sequence is empty -- nothing to protect.")

    normalized = sequence.upper()
    invalid_chars = sorted(set(normalized) - VALID_BASES_SET)
    if invalid_chars:
        raise DNAErrorCorrectionError(
            "DNA sequence contains invalid character(s): "
            f"{', '.join(repr(c) for c in invalid_chars)}. "
            "Only A, T, G, C (any case) are allowed."
        )

    return normalized


def _validate_block_and_redundancy_size(block_size: int, redundancy_size: int) -> None:
    """Validate block_size and redundancy_size are sane positive integers."""
    if isinstance(block_size, bool) or not isinstance(block_size, int) or block_size < 1:
        raise DNAErrorCorrectionError("Block size must be a positive whole number.")
    if block_size > MAX_BLOCK_SIZE:
        raise DNAErrorCorrectionError(
            f"Block size is too large (max {MAX_BLOCK_SIZE} for this educational demo)."
        )

    if (
        isinstance(redundancy_size, bool)
        or not isinstance(redundancy_size, int)
        or redundancy_size < 1
    ):
        raise DNAErrorCorrectionError("Redundancy size must be a positive whole number.")
    if redundancy_size > MAX_REDUNDANCY_SIZE:
        raise DNAErrorCorrectionError(
            f"Redundancy size is too large (max {MAX_REDUNDANCY_SIZE} for this educational demo)."
        )


def _checksum_base(block: str) -> str:
    """Compute the single-base checksum for one block of DNA."""
    checksum_value = sum(BASE_VALUE[base] for base in block) % 4
    return VALUE_TO_BASE[checksum_value]


def _majority_base(bases: str):
    """Return the most common character in `bases`, or None if there's a tie
    (including the case where `bases` is empty)."""
    if len(bases) == 0:
        return None
    counts = Counter(bases)
    ranked = counts.most_common()
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None  # tie -- ambiguous, no clear majority
    return ranked[0][0]


def _expected_protected_length(original_length: int, block_size: int, redundancy_size: int) -> int:
    """Total length a protected sequence should have for the given inputs."""
    if original_length <= 0:
        return 0
    num_blocks = (original_length + block_size - 1) // block_size  # ceiling division
    return original_length + num_blocks * redundancy_size


def _split_protected(protected_sequence: str, original_length: int, block_size: int, redundancy_size: int):
    """Split a protected sequence back into (block, redundancy) pairs.

    Raises DNAErrorCorrectionError if the sequence length doesn't match
    what block_size/redundancy_size/original_length predict -- this is
    never guessed at or repaired.
    """
    expected_len = _expected_protected_length(original_length, block_size, redundancy_size)
    if len(protected_sequence) != expected_len:
        raise DNAErrorCorrectionError(
            f"Sequence length ({len(protected_sequence)}) does not match the "
            f"expected protected length ({expected_len}) for {original_length} "
            "data base(s). The block structure cannot be reliably located."
        )

    blocks = []
    pos = 0
    remaining_data = original_length
    while remaining_data > 0:
        this_block_len = min(block_size, remaining_data)
        block = protected_sequence[pos : pos + this_block_len]
        pos += this_block_len
        redundancy = protected_sequence[pos : pos + redundancy_size]
        pos += redundancy_size
        blocks.append((block, redundancy))
        remaining_data -= this_block_len

    return blocks


def add_redundancy(sequence: str, block_size: int = DEFAULT_BLOCK_SIZE, redundancy_size: int = DEFAULT_REDUNDANCY_SIZE) -> dict:
    """Add block-checksum redundancy to a DNA sequence.

    Returns a dict with the protected sequence plus the parameters
    needed later to detect/correct/remove that redundancy (block_size,
    redundancy_size, and the original unprotected length).
    """
    normalized = validate_dna_sequence(sequence)
    _validate_block_and_redundancy_size(block_size, redundancy_size)

    protected_parts = []
    for i in range(0, len(normalized), block_size):
        block = normalized[i : i + block_size]
        checksum_base = _checksum_base(block)
        protected_parts.append(block + checksum_base * redundancy_size)

    protected_sequence = "".join(protected_parts)

    return {
        "protected_sequence": protected_sequence,
        "original_length": len(normalized),
        "block_size": block_size,
        "redundancy_size": redundancy_size,
    }


def detect_errors(received_sequence: str, block_size: int, redundancy_size: int, original_length: int) -> dict:
    """Check a (possibly mutated) protected sequence for checksum errors.

    Does NOT modify the sequence. Returns which blocks failed their
    checksum check, or reports a structural length mismatch when the
    sequence can't be split into blocks at all (a sign of insertions
    or deletions, which this method cannot pinpoint).
    """
    normalized = validate_dna_sequence(received_sequence)
    _validate_block_and_redundancy_size(block_size, redundancy_size)

    expected_len = _expected_protected_length(original_length, block_size, redundancy_size)
    if len(normalized) != expected_len:
        return {
            "length_matches_expected": False,
            "blocks_checked": 0,
            "error_block_indices": [],
            "errors_detected": None,
            "message": (
                f"Received sequence length ({len(normalized)}) does not match "
                f"the expected protected length ({expected_len}). This usually "
                "means bases were inserted or deleted -- block-level checksum "
                "detection cannot be performed reliably in that case."
            ),
        }

    blocks = _split_protected(normalized, original_length, block_size, redundancy_size)
    error_indices = []
    for idx, (block, redundancy) in enumerate(blocks):
        expected_checksum_base = _checksum_base(block)
        stored_checksum_base = _majority_base(redundancy)
        if stored_checksum_base is None or stored_checksum_base != expected_checksum_base:
            error_indices.append(idx)

    if error_indices:
        message = f"{len(error_indices)} of {len(blocks)} block(s) failed checksum verification."
    else:
        message = f"All {len(blocks)} block(s) passed checksum verification -- no errors detected."

    return {
        "length_matches_expected": True,
        "blocks_checked": len(blocks),
        "error_block_indices": error_indices,
        "errors_detected": len(error_indices),
        "message": message,
    }


def correct_substitution_errors(received_sequence: str, block_size: int, redundancy_size: int, original_length: int) -> dict:
    """Attempt to detect and correct substitution errors in a protected sequence.

    For each block whose checksum doesn't match, tries every possible
    single-base substitution to see if exactly one of them restores a
    matching checksum. Only applies a fix when that match is unique --
    otherwise the block is left as received and counted as
    uncorrectable. Never claims success when the result is uncertain.
    """
    normalized = validate_dna_sequence(received_sequence)
    _validate_block_and_redundancy_size(block_size, redundancy_size)

    detection = detect_errors(normalized, block_size, redundancy_size, original_length)

    if not detection["length_matches_expected"]:
        return {
            "received_sequence": normalized,
            "corrected_sequence": None,
            "blocks_checked": 0,
            "errors_detected": None,
            "errors_corrected": 0,
            "uncorrectable_errors": None,
            "correction_success": False,
            "message": detection["message"],
        }

    blocks = _split_protected(normalized, original_length, block_size, redundancy_size)
    corrected_blocks = []
    corrected_count = 0
    uncorrectable_count = 0

    for block, redundancy in blocks:
        stored_checksum_base = _majority_base(redundancy)
        current_checksum_base = _checksum_base(block)

        if stored_checksum_base is not None and current_checksum_base == stored_checksum_base:
            corrected_blocks.append(block)  # this block's checksum already matches
            continue

        if stored_checksum_base is None:
            # The redundancy copies themselves have no clear majority --
            # we cannot know what the "correct" checksum should be.
            corrected_blocks.append(block)
            uncorrectable_count += 1
            continue

        # Try every single-base substitution to see if exactly one
        # restores a matching checksum.
        candidate_blocks = set()
        for pos in range(len(block)):
            original_base = block[pos]
            for alt_base in VALID_BASES:
                if alt_base == original_base:
                    continue
                trial_block = block[:pos] + alt_base + block[pos + 1 :]
                if _checksum_base(trial_block) == stored_checksum_base:
                    candidate_blocks.add(trial_block)

        if len(candidate_blocks) == 1:
            corrected_blocks.append(next(iter(candidate_blocks)))
            corrected_count += 1
        else:
            # Zero matches (multiple errors overwhelmed the checksum) or
            # more than one match (ambiguous) -- refuse to guess.
            corrected_blocks.append(block)
            uncorrectable_count += 1

    corrected_sequence = "".join(corrected_blocks)
    errors_detected = detection["errors_detected"]
    correction_success = errors_detected == 0 or (
        uncorrectable_count == 0 and corrected_count == errors_detected
    )

    if errors_detected == 0:
        message = f"No errors detected across {detection['blocks_checked']} block(s); sequence unchanged."
    elif correction_success:
        message = f"Detected {errors_detected} error(s) and corrected all of them."
    else:
        message = (
            f"Detected {errors_detected} error(s): corrected {corrected_count}, "
            f"but {uncorrectable_count} could not be corrected with confidence "
            "(no unique single-base fix matched the stored checksum)."
        )

    return {
        "received_sequence": normalized,
        "corrected_sequence": corrected_sequence,
        "blocks_checked": detection["blocks_checked"],
        "errors_detected": errors_detected,
        "errors_corrected": corrected_count,
        "uncorrectable_errors": uncorrectable_count,
        "correction_success": correction_success,
        "message": message,
    }


def remove_redundancy(protected_sequence: str, block_size: int, redundancy_size: int, original_length: int) -> str:
    """Strip redundancy bases from a protected sequence, returning pure data.

    Raises DNAErrorCorrectionError (rather than guessing) if the given
    sequence's length doesn't match the expected protected length.
    """
    normalized = validate_dna_sequence(protected_sequence)
    _validate_block_and_redundancy_size(block_size, redundancy_size)

    blocks = _split_protected(normalized, original_length, block_size, redundancy_size)
    return "".join(block for block, _redundancy in blocks)
