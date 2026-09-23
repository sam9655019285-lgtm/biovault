"""
DNA storage reliability, redundancy, and recovery simulation logic
(non-UI, no Streamlit dependency).

EDUCATIONAL SIMULATION ONLY. This module demonstrates a general idea
from data-storage theory -- "storing additional redundant copies can
increase the ability to detect or recover from data loss or
corruption" -- using BioVault's own simulated DNA sequences. It is NOT
a claim about real laboratory DNA-storage performance, and it never
guarantees recovery: redundancy only ever gives recovery a *chance*,
and this module reports honestly whenever that chance did not pay off.

It never touches the real encode/decode pipeline (dna_encoder.py /
dna_decoder.py) or modifies any stored DNA sequence -- it only reads
an existing sequence and works on independent copies/derived values,
reusing dna_mutator.py (corruption), dna_decoder.py (decoding and
comparison), dna_error_correction.py (Phase 6's checksum method, for
side-by-side comparison), and dna_integrity.py's comparison helper.

REDUNDANCY vs. ERROR CORRECTION (see documentation.py for the
beginner-friendly version):
- "Redundancy" here means storing multiple WHOLE independent copies of
  the same DNA sequence, and comparing them base-by-base to guess which
  base was most likely correct at each position ("majority vote").
- "Error correction" (Phase 6, dna_error_correction.py) instead adds a
  small CHECKSUM alongside blocks of the ORIGINAL sequence (not full
  copies), and uses that checksum to detect and, in limited cases,
  correct a single error per block.
Both are redundancy in the general sense (extra information beyond the
minimum needed), but they work very differently and have different
storage costs and failure modes -- this module lets you compare them.
"""

from collections import Counter

from app.modules.dna_encoder import BITS_TO_BASE
from app.modules.dna_decoder import DNADecodingError, decode_dna_to_file
from app.modules.dna_mutator import DNAMutationError, mutate_dna
from app.modules.dna_error_correction import (
    DEFAULT_BLOCK_SIZE,
    DEFAULT_REDUNDANCY_SIZE,
    DNAErrorCorrectionError,
    add_redundancy,
    detect_errors,
    correct_substitution_errors,
)
from app.modules.dna_integrity import compare_original_and_recovered
from app.modules.file_handler import compute_content_hash

VALID_BASES = tuple(BITS_TO_BASE.values())  # ("A", "C", "G", "T")
VALID_BASES_SET = set(VALID_BASES)

# The character used to mark a position this simulation could not
# resolve. It is NOT a valid DNA base on purpose: attempting to decode
# a recovered sequence that still contains this marker will correctly
# fail BioVault's real, strict decoder rather than silently guessing.
UNRESOLVED_MARKER = "?"

# Redundancy levels named by how many EXTRA whole copies are stored
# beyond the original -- e.g. "2 extra copies" means 3 copies exist in
# total. More extra copies means more chances for majority vote to
# out-vote a single corrupted copy, but also more storage used -- this
# module never claims more redundancy is automatically "better" in any
# absolute sense, only that it changes the trade-off (see
# calculate_storage_overhead()).
REDUNDANCY_LEVELS = {
    "No redundancy (1 copy)": 0,
    "1 extra copy (2 copies)": 1,
    "2 extra copies (3 copies)": 2,
    "3 extra copies (4 copies)": 3,
}

RECOVERY_STRATEGY_MAJORITY = "majority_vote"
RECOVERY_STRATEGY_AGREEMENT = "agreement_based"
RECOVERY_STRATEGY_ERROR_CORRECTION = "error_correction"

DEFAULT_AGREEMENT_FRACTION = 0.5

STATUS_RECOVERED = "recovered"
STATUS_PARTIALLY_RECOVERED = "partially_recovered"
STATUS_FAILED = "failed"
STATUS_UNABLE_TO_VERIFY = "unable_to_verify"

DEFAULT_CORRUPTION_RATES_PERCENT = (0.0, 5.0, 10.0, 20.0)
DEFAULT_REDUNDANCY_LEVELS_FOR_EXPERIMENT = (0, 1, 2, 3)


class RedundancySimulationError(Exception):
    """Raised when redundancy-simulation inputs are invalid."""


# --- A/3. Redundancy levels & redundant copies ----------------------------------

def create_redundant_copies(dna_sequence: str, extra_copies: int) -> dict:
    """Create `extra_copies` additional logical copies of `dna_sequence`
    (total_copies = extra_copies + 1).

    Memory-safe by construction: Python strings are immutable, so a
    list of identical, uncorrupted copies is just `total_copies`
    references to the SAME string object -- no extra memory is used
    until (and unless) a copy is later corrupted into a different
    string. The original `dna_sequence` itself is never modified.
    """
    if not isinstance(dna_sequence, str):
        raise RedundancySimulationError("dna_sequence must be a string.")
    if isinstance(extra_copies, bool) or not isinstance(extra_copies, int) or extra_copies < 0:
        raise RedundancySimulationError("extra_copies must be a non-negative whole number.")

    total_copies = extra_copies + 1
    return {
        "dna_sequence": dna_sequence,
        "dna_length": len(dna_sequence),
        "extra_copies": extra_copies,
        "total_copies": total_copies,
        "copies": [dna_sequence] * total_copies,
    }


def calculate_storage_overhead(dna_length: int, extra_copies: int) -> dict:
    """Return the simplified storage cost of keeping `extra_copies`
    extra whole copies of a `dna_length`-base sequence.

    This is a SIMPLIFIED model: it only counts DNA bases, exactly like
    storage_analysis.py's own "raw" figures -- it does not model real
    synthesis/sequencing/addressing costs for multiple physical copies.
    """
    if isinstance(dna_length, bool) or not isinstance(dna_length, int) or dna_length < 0:
        raise RedundancySimulationError("dna_length must be a non-negative whole number.")
    if isinstance(extra_copies, bool) or not isinstance(extra_copies, int) or extra_copies < 0:
        raise RedundancySimulationError("extra_copies must be a non-negative whole number.")

    total_copies = extra_copies + 1
    total_length = dna_length * total_copies
    additional_bases = total_length - dna_length
    overhead_percent = round((additional_bases / dna_length) * 100, 2) if dna_length > 0 else 0.0

    return {
        "original_dna_length": dna_length,
        "extra_copies": extra_copies,
        "total_copies": total_copies,
        "storage_multiplier": total_copies,
        "total_dna_length": total_length,
        "additional_bases": additional_bases,
        "overhead_percent": overhead_percent,
    }


# --- 4. Simulate corruption ------------------------------------------------------

def corrupt_copies(
    copies: list,
    mutation_type: str,
    mutation_rate: float,
    seed: int = None,
) -> dict:
    """Independently corrupt each entry in `copies` using the existing
    Phase 5 mutator (dna_mutator.mutate_dna), operating on copies of the
    input list/strings -- `copies` itself and its string contents are
    never modified in place (strings are immutable and a new list is
    always returned).

    Each copy gets its OWN derived seed (`seed + index`, when a seed is
    given) so that, with a moderate mutation rate, different copies are
    very unlikely to end up corrupted in exactly the same way -- this
    is what gives majority voting a real chance to out-vote a single
    corrupted copy. Passing the same seed to every copy would make
    every copy mutate identically, defeating the entire point of the
    demonstration.

    A mutation_rate of 0 is valid and simply leaves every copy
    unchanged (still passed through mutate_dna for a consistent stats
    shape, except for an empty sequence which mutate_dna rejects).
    """
    if not isinstance(copies, (list, tuple)):
        raise RedundancySimulationError("copies must be a list of DNA sequence strings.")

    corrupted_copies = []
    per_copy_results = []
    corrupted_copy_count = 0

    for index, copy in enumerate(copies):
        copy_seed = None if seed is None else seed + index
        if len(copy) == 0:
            # mutate_dna rejects empty input outright; an empty sequence
            # has nothing to corrupt, so it is left as-is.
            corrupted_copies.append(copy)
            per_copy_results.append(None)
            continue

        try:
            mutation_result = mutate_dna(copy, mutation_type, mutation_rate, copy_seed)
        except DNAMutationError as exc:
            raise RedundancySimulationError(f"Could not corrupt copy {index}: {exc}") from exc

        mutated_sequence = mutation_result["mutated_sequence"]
        corrupted_copies.append(mutated_sequence)
        per_copy_results.append(mutation_result)
        if mutated_sequence != copy:
            corrupted_copy_count += 1

    return {
        "mutation_type": mutation_type,
        "mutation_rate": mutation_rate,
        "seed": seed,
        "copies": corrupted_copies,
        "per_copy_results": per_copy_results,
        "corrupted_copy_count": corrupted_copy_count,
        "total_copies": len(copies),
    }


# --- 6. Alignment check (insertion/deletion safety) ------------------------------

def check_alignment(copies: list) -> dict:
    """Check whether every copy in `copies` has the SAME length.

    Majority voting by character position is only meaningful when
    every copy is aligned (same length) -- an insertion or deletion in
    even one copy shifts everything after it, so comparing by raw
    index would silently compare unrelated positions. This function
    never guesses at an alignment; it only reports whether one exists.
    """
    if not isinstance(copies, (list, tuple)) or len(copies) == 0:
        raise RedundancySimulationError("copies must be a non-empty list of DNA sequence strings.")

    lengths = [len(copy) for copy in copies]
    unique_lengths = sorted(set(lengths))
    is_aligned = len(unique_lengths) == 1

    return {
        "is_aligned": is_aligned,
        "copy_lengths": lengths,
        "common_length": unique_lengths[0] if is_aligned else None,
    }


# --- 5. Recovery Strategy A -- Majority vote -------------------------------------

def majority_vote_recovery(copies: list) -> dict:
    """Recover a sequence by comparing corresponding bases across
    `copies` position-by-position, picking whichever base is strictly
    the most common at each position. A position with no single
    strict winner (a tie for the top count) is marked unresolved with
    UNRESOLVED_MARKER rather than guessed at.

    Requires every copy to be the same length (see check_alignment());
    if they are not, this function reports that directly rather than
    attempting a misleading comparison.
    """
    alignment = check_alignment(copies)
    if not alignment["is_aligned"]:
        return {
            "strategy": RECOVERY_STRATEGY_MAJORITY,
            "alignment_available": False,
            "copy_lengths": alignment["copy_lengths"],
            "recovered_sequence": None,
            "total_positions": None,
            "recoverable_position_count": None,
            "unresolved_position_count": None,
            "unresolved_positions": None,
            "message": (
                "Copies have different lengths (likely from an insertion or "
                "deletion), so position-by-position majority voting cannot "
                "be performed reliably. Direct majority recovery is "
                "unavailable for this data."
            ),
        }

    length = alignment["common_length"]
    recovered_chars = []
    unresolved_positions = []

    for position in range(length):
        bases_at_position = [copy[position] for copy in copies]
        counts = Counter(bases_at_position)
        ranked = counts.most_common()
        has_clear_majority = len(ranked) == 1 or ranked[0][1] > ranked[1][1]
        if has_clear_majority:
            recovered_chars.append(ranked[0][0])
        else:
            recovered_chars.append(UNRESOLVED_MARKER)
            unresolved_positions.append(position)

    return {
        "strategy": RECOVERY_STRATEGY_MAJORITY,
        "alignment_available": True,
        "copy_lengths": alignment["copy_lengths"],
        "recovered_sequence": "".join(recovered_chars),
        "total_positions": length,
        "recoverable_position_count": length - len(unresolved_positions),
        "unresolved_position_count": len(unresolved_positions),
        "unresolved_positions": unresolved_positions,
        "message": None,
    }


# --- 5. Recovery Strategy B -- Agreement-based recovery --------------------------

def agreement_based_recovery(copies: list, min_agreement_fraction: float = DEFAULT_AGREEMENT_FRACTION) -> dict:
    """Like majority_vote_recovery(), but stricter: a position is only
    recovered when its most common base is both a strict winner AND
    appears in at least `min_agreement_fraction` of all copies (not
    just the most common among possibly-weak, scattered votes).

    This directly demonstrates the difference between "the most common
    answer" (Strategy A) and "an answer most copies actually agree on"
    (Strategy B) -- with few copies or a low agreement fraction the two
    often coincide, but they can diverge once several copies disagree
    in different ways.
    """
    if not isinstance(min_agreement_fraction, (int, float)) or isinstance(min_agreement_fraction, bool):
        raise RedundancySimulationError("min_agreement_fraction must be a number between 0 and 1.")
    if not (0 < min_agreement_fraction <= 1):
        raise RedundancySimulationError("min_agreement_fraction must be greater than 0 and at most 1.")

    alignment = check_alignment(copies)
    if not alignment["is_aligned"]:
        return {
            "strategy": RECOVERY_STRATEGY_AGREEMENT,
            "alignment_available": False,
            "copy_lengths": alignment["copy_lengths"],
            "recovered_sequence": None,
            "total_positions": None,
            "recoverable_position_count": None,
            "unresolved_position_count": None,
            "unresolved_positions": None,
            "min_agreement_fraction": min_agreement_fraction,
            "message": (
                "Copies have different lengths (likely from an insertion or "
                "deletion), so position-by-position agreement checking "
                "cannot be performed reliably. Direct recovery is "
                "unavailable for this data."
            ),
        }

    length = alignment["common_length"]
    total_copies = len(copies)
    required_count = min_agreement_fraction * total_copies

    recovered_chars = []
    unresolved_positions = []

    for position in range(length):
        bases_at_position = [copy[position] for copy in copies]
        counts = Counter(bases_at_position)
        ranked = counts.most_common()
        top_base, top_count = ranked[0]
        has_clear_majority = len(ranked) == 1 or top_count > ranked[1][1]

        if has_clear_majority and top_count >= required_count:
            recovered_chars.append(top_base)
        else:
            recovered_chars.append(UNRESOLVED_MARKER)
            unresolved_positions.append(position)

    return {
        "strategy": RECOVERY_STRATEGY_AGREEMENT,
        "alignment_available": True,
        "copy_lengths": alignment["copy_lengths"],
        "recovered_sequence": "".join(recovered_chars),
        "total_positions": length,
        "recoverable_position_count": length - len(unresolved_positions),
        "unresolved_position_count": len(unresolved_positions),
        "unresolved_positions": unresolved_positions,
        "min_agreement_fraction": min_agreement_fraction,
        "message": None,
    }


# --- 5. Recovery Strategy C -- existing Phase 6 error correction ----------------

def error_correction_recovery(
    dna_sequence: str,
    block_size: int = DEFAULT_BLOCK_SIZE,
    redundancy_size: int = DEFAULT_REDUNDANCY_SIZE,
) -> dict:
    """Run BioVault's real, existing Phase 6 checksum-based error
    correction (dna_error_correction.py) on a SINGLE sequence, for
    side-by-side comparison with the whole-copy redundancy strategies
    above. This does not reimplement or modify that algorithm -- it
    only calls it.

    This is fundamentally a DIFFERENT approach from Strategies A/B: it
    adds a small checksum next to blocks of ONE sequence, rather than
    storing multiple whole copies -- see this module's docstring for
    the conceptual difference.
    """
    if not isinstance(dna_sequence, str):
        raise RedundancySimulationError("dna_sequence must be a string.")

    try:
        protection = add_redundancy(dna_sequence, block_size, redundancy_size)
    except DNAErrorCorrectionError as exc:
        raise RedundancySimulationError(f"Could not add error-correction redundancy: {exc}") from exc

    protected_sequence = protection["protected_sequence"]
    original_length = protection["original_length"]

    detection = detect_errors(protected_sequence, block_size, redundancy_size, original_length)
    correction = correct_substitution_errors(protected_sequence, block_size, redundancy_size, original_length)

    return {
        "strategy": RECOVERY_STRATEGY_ERROR_CORRECTION,
        "protected_sequence": protected_sequence,
        "block_size": block_size,
        "redundancy_size": redundancy_size,
        "detection": detection,
        "correction": correction,
        "recovered_sequence": correction["corrected_sequence"],
    }


# --- 7/8. Full simulation: ties everything together into one report -------------

def run_redundancy_simulation(
    dna_sequence: str,
    original_bytes: bytes = None,
    extra_copies: int = 1,
    mutation_type: str = "substitution",
    mutation_rate: float = 5.0,
    seed: int = None,
    recovery_strategy: str = RECOVERY_STRATEGY_MAJORITY,
    agreement_fraction: float = DEFAULT_AGREEMENT_FRACTION,
) -> dict:
    """Run one full educational redundancy/recovery simulation and
    return a single structured report.

    `recovery_confirmed` is True ONLY when the recovered bytes are
    actually compared, byte-for-byte, against `original_bytes` and
    found identical -- never inferred from a high recovery percentage
    or from decoding "succeeding" in isolation.
    """
    if not isinstance(dna_sequence, str) or len(dna_sequence) == 0:
        raise RedundancySimulationError("dna_sequence must be a non-empty string.")
    if recovery_strategy not in (
        RECOVERY_STRATEGY_MAJORITY,
        RECOVERY_STRATEGY_AGREEMENT,
        RECOVERY_STRATEGY_ERROR_CORRECTION,
    ):
        raise RedundancySimulationError(f"Unknown recovery_strategy: {recovery_strategy!r}.")

    redundancy_info = create_redundant_copies(dna_sequence, extra_copies)
    overhead_info = calculate_storage_overhead(len(dna_sequence), extra_copies)
    corruption_info = corrupt_copies(redundancy_info["copies"], mutation_type, mutation_rate, seed)

    recovery_detail = None
    recovered_sequence = None
    total_positions = None
    recoverable_position_count = None
    unresolved_position_count = None

    if recovery_strategy == RECOVERY_STRATEGY_ERROR_CORRECTION:
        # Demonstrates the OTHER approach on the first (possibly
        # corrupted) copy -- a genuinely different technique, not
        # whole-copy majority voting.
        recovery_detail = error_correction_recovery(corruption_info["copies"][0])
        recovered_sequence = recovery_detail["recovered_sequence"]
        correction = recovery_detail["correction"]
        total_positions = correction["blocks_checked"]
        recoverable_position_count = None if correction["errors_detected"] is None else (
            correction["blocks_checked"] - (correction["uncorrectable_errors"] or 0)
        )
        unresolved_position_count = correction["uncorrectable_errors"]
    else:
        recovery_fn = majority_vote_recovery if recovery_strategy == RECOVERY_STRATEGY_MAJORITY else agreement_based_recovery
        kwargs = {} if recovery_strategy == RECOVERY_STRATEGY_MAJORITY else {"min_agreement_fraction": agreement_fraction}
        recovery_detail = recovery_fn(corruption_info["copies"], **kwargs)
        recovered_sequence = recovery_detail["recovered_sequence"]
        total_positions = recovery_detail["total_positions"]
        recoverable_position_count = recovery_detail["recoverable_position_count"]
        unresolved_position_count = recovery_detail["unresolved_position_count"]

    recovery_percentage = (
        round((recoverable_position_count / total_positions) * 100, 2)
        if total_positions else 0.0
    )

    can_decode = False
    decoded_bytes = None
    if recovered_sequence:
        try:
            decoded = decode_dna_to_file(recovered_sequence)
            decoded_bytes = decoded["recovered_bytes"]
            can_decode = True
        except DNADecodingError:
            can_decode = False

    original_hash = compute_content_hash(original_bytes) if original_bytes is not None else None
    recovered_hash = compute_content_hash(decoded_bytes) if decoded_bytes is not None else None
    comparison_result = None
    recovery_confirmed = None
    exact_byte_recovery = None

    if original_bytes is not None:
        if can_decode:
            comparison_result = compare_original_and_recovered(original_bytes, decoded_bytes)
            recovery_confirmed = comparison_result["is_identical"]
            exact_byte_recovery = comparison_result["is_identical"]
        else:
            recovery_confirmed = False
            exact_byte_recovery = False

        if recovery_confirmed:
            status = STATUS_RECOVERED
        elif recoverable_position_count and total_positions and recoverable_position_count > 0:
            status = STATUS_PARTIALLY_RECOVERED
        else:
            status = STATUS_FAILED
    else:
        status = STATUS_UNABLE_TO_VERIFY

    return {
        "status": status,
        "recovery_confirmed": recovery_confirmed,
        "exact_byte_recovery": exact_byte_recovery,
        "recovery_percentage": recovery_percentage,
        "can_decode": can_decode,
        "original_dna_length": len(dna_sequence),
        "extra_copies": extra_copies,
        "total_copies": redundancy_info["total_copies"],
        "storage_overhead": overhead_info,
        "mutation_type": mutation_type,
        "mutation_rate": mutation_rate,
        "seed": seed,
        "corrupted_copy_count": corruption_info["corrupted_copy_count"],
        "total_positions": total_positions,
        "recoverable_position_count": recoverable_position_count,
        "unresolved_position_count": unresolved_position_count,
        "recovery_strategy": recovery_strategy,
        "recovery_detail": recovery_detail,
        "recovered_sequence": recovered_sequence,
        "original_hash": original_hash,
        "recovered_hash": recovered_hash,
        "comparison_result": comparison_result,
    }


# --- 9. Reliability experiment across multiple corruption/redundancy levels -----

def run_reliability_experiment(
    dna_sequence: str,
    original_bytes: bytes = None,
    redundancy_levels=DEFAULT_REDUNDANCY_LEVELS_FOR_EXPERIMENT,
    corruption_rates=DEFAULT_CORRUPTION_RATES_PERCENT,
    mutation_type: str = "substitution",
    seed: int = 0,
) -> list:
    """Run run_redundancy_simulation() once for every combination of
    `redundancy_levels` x `corruption_rates`, using majority-vote
    recovery, and return one row per combination.

    Every value returned is generated by actually running the
    simulation -- nothing here is a hardcoded or precomputed result.
    Deterministic for a fixed `seed`.
    """
    if not isinstance(dna_sequence, str) or len(dna_sequence) == 0:
        raise RedundancySimulationError("dna_sequence must be a non-empty string.")

    results = []
    for level in redundancy_levels:
        for rate in corruption_rates:
            simulation = run_redundancy_simulation(
                dna_sequence,
                original_bytes=original_bytes,
                extra_copies=level,
                mutation_type=mutation_type,
                mutation_rate=rate,
                seed=seed,
                recovery_strategy=RECOVERY_STRATEGY_MAJORITY,
            )
            results.append(
                {
                    "redundancy_level": level,
                    "total_copies": level + 1,
                    "corruption_rate_percent": rate,
                    "recovery_percentage": simulation["recovery_percentage"],
                    "recovery_confirmed": simulation["recovery_confirmed"],
                    "status": simulation["status"],
                    "storage_overhead_percent": simulation["storage_overhead"]["overhead_percent"],
                }
            )
    return results
