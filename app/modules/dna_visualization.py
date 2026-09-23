"""
DNA data visualization logic (non-UI, no Streamlit dependency).

This module prepares small, predictable Pandas DataFrames and
dictionaries from data already produced elsewhere in BioVault (Phase 3
encoding, Phase 5 mutation, Phase 6 error correction, Phase 7 storage
analysis) so the Streamlit page can render charts without doing any
calculation itself. It never invents data -- every function that needs
an optional result (mutation/correction/storage) simply returns None
or an explanatory message when that result isn't available, rather
than fabricating placeholder numbers.

IMPORTANT: Everything here visualizes computational simulation output.
None of it is a measurement of real, physical DNA.
"""

import pandas as pd

from app.modules.dna_encoder import BITS_TO_BASE

VALID_BASES = tuple(BITS_TO_BASE.values())  # ("A", "C", "G", "T")
VALID_BASES_SET = set(VALID_BASES)


class DNAVisualizationError(Exception):
    """Raised when DNA data given to a visualization function is invalid."""


def validate_dna_sequence(sequence: str) -> str:
    """Validate a DNA sequence and return it normalized to uppercase.

    Same rules used throughout BioVault: non-empty, only A/T/G/C (any
    case, normalized to uppercase). Invalid characters are rejected
    rather than silently stripped.
    """
    if not isinstance(sequence, str):
        raise DNAVisualizationError("DNA sequence must be a string.")

    if len(sequence) == 0:
        raise DNAVisualizationError("DNA sequence is empty -- nothing to visualize.")

    normalized = sequence.upper()
    invalid_chars = sorted(set(normalized) - VALID_BASES_SET)
    if invalid_chars:
        raise DNAVisualizationError(
            "DNA sequence contains invalid character(s): "
            f"{', '.join(repr(c) for c in invalid_chars)}. "
            "Only A, T, G, C (any case) are allowed."
        )

    return normalized


def count_dna_bases(sequence: str) -> dict:
    """Count occurrences of each base (A, T, G, C) plus the total length.

    All four bases are always included in the result (as 0 if absent)
    so charts and tables stay consistent even for lopsided sequences.
    """
    normalized = validate_dna_sequence(sequence)
    counts = {base: 0 for base in VALID_BASES}
    for base in normalized:
        counts[base] += 1

    counts["total"] = len(normalized)
    return counts


def calculate_base_percentages(sequence: str) -> dict:
    """Return each base's share of the sequence as a percentage.

    Percentages are rounded to 2 decimal places; because of rounding,
    their sum may differ from exactly 100 by a small fraction (this is
    normal and expected, not a bug).
    """
    counts = count_dna_bases(sequence)
    total = counts["total"]

    return {base: round((counts[base] / total) * 100, 2) for base in VALID_BASES}


def prepare_base_composition_data(sequence: str) -> pd.DataFrame:
    """Build a DataFrame of Base / Count / Percentage for charts and tables."""
    counts = count_dna_bases(sequence)
    percentages = calculate_base_percentages(sequence)

    return pd.DataFrame(
        {
            "Base": list(VALID_BASES),
            "Count": [counts[base] for base in VALID_BASES],
            "Percentage": [percentages[base] for base in VALID_BASES],
        }
    )


def prepare_length_comparison_data(original_length: int, mutated_length: int = None, protected_length: int = None) -> pd.DataFrame:
    """Build a DataFrame comparing DNA lengths across pipeline stages.

    Only includes rows for lengths that were actually provided --
    missing optional values (None) are left out entirely rather than
    shown as a misleading 0.
    """
    if not isinstance(original_length, int) or isinstance(original_length, bool) or original_length < 0:
        raise DNAVisualizationError("original_length must be a non-negative whole number.")

    labels = ["Original DNA"]
    lengths = [original_length]

    if mutated_length is not None:
        if not isinstance(mutated_length, int) or isinstance(mutated_length, bool) or mutated_length < 0:
            raise DNAVisualizationError("mutated_length must be a non-negative whole number.")
        labels.append("Mutated DNA")
        lengths.append(mutated_length)

    if protected_length is not None:
        if not isinstance(protected_length, int) or isinstance(protected_length, bool) or protected_length < 0:
            raise DNAVisualizationError("protected_length must be a non-negative whole number.")
        labels.append("Protected DNA")
        lengths.append(protected_length)

    return pd.DataFrame({"Stage": labels, "Length (bases)": lengths})


def prepare_mutation_statistics_data(mutation_stats: dict):
    """Summarize Phase 5 mutation stats for display, plus an edit-type chart.

    `mutation_stats` is the stats dict produced by dna_mutator.mutate_dna()
    (substitutions/insertions/deletions were tallied during the mutation
    itself, not re-derived by comparing sequences afterward -- this
    function simply formats that existing data, it does not recompute
    anything with zip() or positional comparison). Returns None if the
    required fields aren't present, rather than inventing values.
    """
    required_fields = {
        "original_length", "mutated_length", "mutation_type", "mutation_rate",
        "substitutions", "insertions", "deletions", "total_edits",
    }
    if not isinstance(mutation_stats, dict) or not required_fields <= set(mutation_stats.keys()):
        return None

    length_difference = mutation_stats["mutated_length"] - mutation_stats["original_length"]

    summary = {
        "mutation_type": mutation_stats["mutation_type"],
        "mutation_rate": mutation_stats["mutation_rate"],
        "original_length": mutation_stats["original_length"],
        "mutated_length": mutation_stats["mutated_length"],
        "length_difference": length_difference,
        "length_changed": length_difference != 0,
        "total_edits": mutation_stats["total_edits"],
    }

    edit_breakdown = pd.DataFrame(
        {
            "Edit Type": ["Substitutions", "Insertions", "Deletions"],
            "Count": [
                mutation_stats["substitutions"],
                mutation_stats["insertions"],
                mutation_stats["deletions"],
            ],
        }
    )

    return {"summary": summary, "edit_breakdown": edit_breakdown}


def prepare_error_correction_data(correction_result: dict):
    """Summarize Phase 6 correction stats for display, plus a bar-chart DataFrame.

    `correction_result` is expected to be the "correction" dict produced
    by dna_error_correction.correct_substitution_errors(). Returns None
    if required fields are missing.
    """
    required_fields = {
        "blocks_checked", "errors_detected", "errors_corrected",
        "uncorrectable_errors", "correction_success",
    }
    if not isinstance(correction_result, dict) or not required_fields <= set(correction_result.keys()):
        return None

    summary = {
        "blocks_checked": correction_result["blocks_checked"],
        "errors_detected": correction_result["errors_detected"],
        "errors_corrected": correction_result["errors_corrected"],
        "uncorrectable_errors": correction_result["uncorrectable_errors"],
        "correction_success": correction_result["correction_success"],
    }

    corrected = correction_result["errors_corrected"] or 0
    uncorrectable = correction_result["uncorrectable_errors"] or 0
    breakdown = pd.DataFrame(
        {
            "Outcome": ["Corrected", "Uncorrectable"],
            "Count": [corrected, uncorrectable],
        }
    )

    return {"summary": summary, "breakdown": breakdown}


def prepare_storage_overhead_data(storage_report: dict):
    """Summarize Phase 7 storage-analysis data for display, plus a bar-chart DataFrame.

    `storage_report` is expected to be the report dict produced by
    storage_analysis.analyze_storage_efficiency(). Returns None if
    required fields are missing. The redundancy-related fields are
    included only when that report actually computed them.
    """
    required_fields = {"file_size_bytes", "capacity_info", "raw_efficiency_percent"}
    if not isinstance(storage_report, dict) or not required_fields <= set(storage_report.keys()):
        return None

    summary = {
        "file_size_bytes": storage_report["file_size_bytes"],
        "dna_length": storage_report["capacity_info"]["dna_length"],
        "raw_efficiency_percent": storage_report["raw_efficiency_percent"],
        "redundancy_bases": None,
        "protected_length": None,
        "overhead_percent": None,
    }

    breakdown_rows = {"Metric": ["Encoded DNA"], "Bases": [storage_report["capacity_info"]["dna_length"]]}

    redundancy_info = storage_report.get("redundancy_info")
    if redundancy_info is not None:
        summary["redundancy_bases"] = redundancy_info["redundancy_bases"]
        summary["protected_length"] = redundancy_info["protected_length"]
        summary["overhead_percent"] = redundancy_info["overhead_percent"]
        breakdown_rows["Metric"].append("Redundancy Overhead")
        breakdown_rows["Bases"].append(redundancy_info["redundancy_bases"])

    breakdown = pd.DataFrame(breakdown_rows)

    return {"summary": summary, "breakdown": breakdown}
