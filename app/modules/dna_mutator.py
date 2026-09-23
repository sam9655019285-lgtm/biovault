"""
DNA mutation / error simulation logic (non-UI, no Streamlit dependency).

This module introduces artificial "errors" into a DNA base sequence to
simulate the kinds of problems that could occur when data is stored on
a real, physical medium: a base is accidentally changed (substitution),
an extra base appears (insertion), or a base goes missing (deletion).

IMPORTANT: This is a pure software simulation. It does not model any
real biological mutation mechanism, DNA synthesis error, or sequencing
error in a scientifically accurate way -- it is a simplified teaching
tool for exploring how errors affect data recovery.

Reuses the same valid-base set as the encoder/decoder (VALID_BASES)
so all three modules always agree on what counts as valid DNA.
"""

import random

from app.modules.dna_encoder import BITS_TO_BASE

VALID_BASES = tuple(BITS_TO_BASE.values())  # ("A", "C", "G", "T")
VALID_BASES_SET = set(VALID_BASES)

MUTATION_TYPES = ("substitution", "insertion", "deletion")


class DNAMutationError(Exception):
    """Raised when a DNA sequence, mutation rate, or mutation type is invalid."""


def validate_dna_sequence(sequence: str) -> str:
    """Validate a DNA sequence and return it normalized to uppercase.

    Same rules as the decoder's validator: non-empty, only A/T/G/C
    (any case, normalized to uppercase), invalid characters are
    rejected rather than silently stripped or repaired.
    """
    if not isinstance(sequence, str):
        raise DNAMutationError("DNA sequence must be a string.")

    if len(sequence) == 0:
        raise DNAMutationError("DNA sequence is empty -- nothing to mutate.")

    normalized = sequence.upper()
    invalid_chars = sorted(set(normalized) - VALID_BASES_SET)
    if invalid_chars:
        raise DNAMutationError(
            "DNA sequence contains invalid character(s): "
            f"{', '.join(repr(c) for c in invalid_chars)}. "
            "Only A, T, G, C (any case) are allowed."
        )

    return normalized


def validate_mutation_rate(mutation_rate: float) -> float:
    """Validate that mutation_rate is a number between 0 and 100 (percent)."""
    if isinstance(mutation_rate, bool) or not isinstance(mutation_rate, (int, float)):
        raise DNAMutationError("Mutation rate must be a number between 0 and 100.")

    if not (0 <= mutation_rate <= 100):
        raise DNAMutationError(
            f"Mutation rate must be between 0 and 100 (got {mutation_rate})."
        )

    return float(mutation_rate)


def substitute_bases(sequence: str, mutation_rate: float, seed: int = None) -> tuple:
    """Randomly replace some bases with a *different* valid base.

    Each base in the sequence is independently substituted with
    probability = mutation_rate / 100. A substituted base is always
    replaced by one of the *other three* bases, so a substitution can
    never "mutate" a base into itself. The sequence length never
    changes.

    Returns (mutated_sequence, substitution_count).
    """
    normalized = validate_dna_sequence(sequence)
    rate = validate_mutation_rate(mutation_rate)
    probability = rate / 100
    rng = random.Random(seed)

    mutated_bases = []
    substitution_count = 0

    for base in normalized:
        if rng.random() < probability:
            other_bases = [b for b in VALID_BASES if b != base]
            new_base = rng.choice(other_bases)
            mutated_bases.append(new_base)
            substitution_count += 1
        else:
            mutated_bases.append(base)

    return "".join(mutated_bases), substitution_count


def insert_bases(sequence: str, mutation_rate: float, seed: int = None) -> tuple:
    """Randomly insert extra valid bases into the sequence.

    Insertion probability: the sequence has len(sequence) + 1 "gap"
    positions (before every base, plus one after the last base). At
    each gap, an insertion happens independently with
    probability = mutation_rate / 100; when it does, one random valid
    base is inserted at that gap. This means the mutated sequence is
    normally longer than the original, and a rate of 0 always leaves
    the sequence unchanged.

    Returns (mutated_sequence, insertion_count).
    """
    normalized = validate_dna_sequence(sequence)
    rate = validate_mutation_rate(mutation_rate)
    probability = rate / 100
    rng = random.Random(seed)

    mutated_bases = []
    insertion_count = 0

    for base in normalized:
        if rng.random() < probability:
            mutated_bases.append(rng.choice(VALID_BASES))
            insertion_count += 1
        mutated_bases.append(base)

    # Final gap, after the last base.
    if rng.random() < probability:
        mutated_bases.append(rng.choice(VALID_BASES))
        insertion_count += 1

    return "".join(mutated_bases), insertion_count


def delete_bases(sequence: str, mutation_rate: float, seed: int = None) -> tuple:
    """Randomly remove some bases from the sequence.

    Deletion probability: each base in the sequence is independently
    removed (excluded from the output) with probability
    = mutation_rate / 100. This means the mutated sequence is normally
    shorter than the original -- it can shrink down to an empty
    string at a 100% rate, but its length can never go negative, and
    a rate of 0 always leaves the sequence unchanged.

    Returns (mutated_sequence, deletion_count).
    """
    normalized = validate_dna_sequence(sequence)
    rate = validate_mutation_rate(mutation_rate)
    probability = rate / 100
    rng = random.Random(seed)

    mutated_bases = []
    deletion_count = 0

    for base in normalized:
        if rng.random() < probability:
            deletion_count += 1
        else:
            mutated_bases.append(base)

    return "".join(mutated_bases), deletion_count


def get_mutation_statistics(
    original_length: int,
    mutated_length: int,
    substitutions: int = 0,
    insertions: int = 0,
    deletions: int = 0,
) -> dict:
    """Build a statistics dict summarizing a mutation run.

    "Total simulated edits" is the sum of edits actually performed
    during the mutation pass itself (tracked while mutating, not
    re-derived afterwards). This avoids the common mistake of using a
    naive zip()-based comparison of original vs. mutated sequences,
    which breaks down as soon as insertions or deletions shift the
    alignment between the two sequences.
    """
    total_edits = substitutions + insertions + deletions
    edit_rate_percent = (
        round((total_edits / original_length) * 100, 2) if original_length > 0 else 0.0
    )

    return {
        "original_length": original_length,
        "mutated_length": mutated_length,
        "substitutions": substitutions,
        "insertions": insertions,
        "deletions": deletions,
        "total_edits": total_edits,
        "edit_rate_percent": edit_rate_percent,
    }


def mutate_dna(sequence: str, mutation_type: str, mutation_rate: float, seed: int = None) -> dict:
    """Run one mutation pass over a DNA sequence and return full results.

    mutation_type must be one of "substitution", "insertion", "deletion".
    Dispatches to the matching function above, then packages the
    mutated sequence together with mutation_statistics so the UI layer
    stays a thin presentation layer.
    """
    if mutation_type not in MUTATION_TYPES:
        raise DNAMutationError(
            f"Unknown mutation type '{mutation_type}'. "
            f"Must be one of: {', '.join(MUTATION_TYPES)}."
        )

    normalized = validate_dna_sequence(sequence)
    original_length = len(normalized)

    if mutation_type == "substitution":
        mutated_sequence, substitutions = substitute_bases(normalized, mutation_rate, seed)
        insertions = deletions = 0
    elif mutation_type == "insertion":
        mutated_sequence, insertions = insert_bases(normalized, mutation_rate, seed)
        substitutions = deletions = 0
    else:  # "deletion"
        mutated_sequence, deletions = delete_bases(normalized, mutation_rate, seed)
        substitutions = insertions = 0

    stats = get_mutation_statistics(
        original_length=original_length,
        mutated_length=len(mutated_sequence),
        substitutions=substitutions,
        insertions=insertions,
        deletions=deletions,
    )

    return {
        "mutated_sequence": mutated_sequence,
        "mutation_type": mutation_type,
        "mutation_rate": mutation_rate,
        "seed": seed,
        **stats,
    }
