"""
DNA storage benchmarking & experiment comparison logic (non-UI, no
Streamlit dependency).

This module does not re-implement any encoding, mutation, or
error-correction logic -- it only reads the result dictionaries those
modules already produce (dna_encoder.encode_file_to_dna,
dna_mutator.mutate_dna, dna_error_correction.correct_substitution_errors)
and arranges them into a clear, honest side-by-side comparison. Every
section is None (or a cell reads "Not available") when its source data
doesn't exist -- nothing here is ever fabricated.

Comparison stages:
    Original  -- the Phase 3 encoded DNA sequence
    Mutated   -- the Phase 5 simulated-error sequence
    Protected -- the Phase 6 redundancy-added sequence
    Corrected -- the Phase 6 post-correction sequence
"""

import pandas as pd

from app.modules.dna_encoder import BITS_PER_BASE
from app.modules.dna_visualization import prepare_length_comparison_data

NOT_AVAILABLE = "Not available"


class BenchmarkingError(Exception):
    """Raised when benchmarking inputs are invalid."""


def calculate_original_statistics(file_info: dict = None, encoding_result: dict = None):
    """Return original-sequence statistics, or None if data isn't available.

    Requires both a real uploaded file and a real Phase 3 encoding
    result -- it never estimates file size from the DNA length or
    vice versa.
    """
    if not file_info or not encoding_result:
        return None

    dna_length = encoding_result.get("dna_length")
    bits_represented = encoding_result.get("binary_length_bits")
    if dna_length is None or bits_represented is None:
        return None

    return {
        "dna_length": dna_length,
        "file_size_bytes": file_info.get("size_bytes"),
        "bits_represented": bits_represented,
        "theoretical_capacity_bits": dna_length * BITS_PER_BASE,
        "bits_per_nucleotide": BITS_PER_BASE,
    }


def calculate_mutation_comparison(mutation_result: dict = None):
    """Return mutation statistics, or None if no mutation result is available."""
    if not mutation_result:
        return None

    stats = mutation_result.get("stats") or {}
    required = {"original_length", "mutated_length", "substitutions", "insertions", "deletions"}
    if not required <= set(stats.keys()):
        return None

    return {
        "original_length": stats["original_length"],
        "mutated_length": stats["mutated_length"],
        "substitutions": stats["substitutions"],
        "insertions": stats["insertions"],
        "deletions": stats["deletions"],
        "mutation_rate": mutation_result.get("mutation_rate"),
    }


def calculate_error_correction_comparison(correction_result: dict = None):
    """Return error-correction statistics, or None if unavailable.

    protected_length / corrected_length are derived from the actual
    sequences produced by Phase 6, not recomputed independently.
    """
    if not correction_result:
        return None

    correction = correction_result.get("correction") or {}
    protected_sequence = correction_result.get("protected_sequence")
    corrected_sequence = correction.get("corrected_sequence")

    return {
        "protected_length": len(protected_sequence) if protected_sequence else None,
        "corrected_length": len(corrected_sequence) if corrected_sequence else None,
        "errors_detected": correction.get("errors_detected"),
        "errors_corrected": correction.get("errors_corrected"),
        "uncorrectable_errors": correction.get("uncorrectable_errors"),
        "correction_success": correction.get("correction_success"),
    }


def calculate_storage_overhead_comparison(original_length, protected_length):
    """Return overhead/efficiency stats, or None if either length is unavailable.

    additional_nucleotides = protected_length - original_length
    overhead_percent = (additional_nucleotides / original_length) * 100
    efficiency_percent = (original_length / protected_length) * 100
    """
    if original_length is None or protected_length is None:
        return None

    for name, value in (("original_length", original_length), ("protected_length", protected_length)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise BenchmarkingError(f"{name} must be a non-negative whole number.")

    additional_nucleotides = protected_length - original_length
    overhead_percent = (
        round((additional_nucleotides / original_length) * 100, 2) if original_length > 0 else 0.0
    )
    efficiency_percent = (
        round((original_length / protected_length) * 100, 2) if protected_length > 0 else 0.0
    )

    return {
        "original_length": original_length,
        "protected_length": protected_length,
        "additional_nucleotides": additional_nucleotides,
        "overhead_percent": overhead_percent,
        "efficiency_percent": efficiency_percent,
    }


def build_comparison_table(original_stats, mutation_stats, correction_stats) -> pd.DataFrame:
    """Build a Metric | Original | Mutated | Protected | Corrected table.

    Any cell whose underlying value doesn't exist is shown as
    "Not available" -- never a fabricated 0 or blank number.
    """

    def cell(value):
        return NOT_AVAILABLE if value is None else value

    original_length = original_stats["dna_length"] if original_stats else None
    mutated_length = mutation_stats["mutated_length"] if mutation_stats else None
    protected_length = correction_stats["protected_length"] if correction_stats else None
    corrected_length = correction_stats["corrected_length"] if correction_stats else None

    rows = [
        {
            "Metric": "Sequence Length (bases)",
            "Original": cell(original_length),
            "Mutated": cell(mutated_length),
            "Protected": cell(protected_length),
            "Corrected": cell(corrected_length),
        },
        {
            "Metric": "File Size (bytes)",
            "Original": cell(original_stats["file_size_bytes"] if original_stats else None),
            "Mutated": NOT_AVAILABLE,
            "Protected": NOT_AVAILABLE,
            "Corrected": NOT_AVAILABLE,
        },
        {
            "Metric": "Substitutions",
            "Original": NOT_AVAILABLE,
            "Mutated": cell(mutation_stats["substitutions"] if mutation_stats else None),
            "Protected": NOT_AVAILABLE,
            "Corrected": NOT_AVAILABLE,
        },
        {
            "Metric": "Insertions",
            "Original": NOT_AVAILABLE,
            "Mutated": cell(mutation_stats["insertions"] if mutation_stats else None),
            "Protected": NOT_AVAILABLE,
            "Corrected": NOT_AVAILABLE,
        },
        {
            "Metric": "Deletions",
            "Original": NOT_AVAILABLE,
            "Mutated": cell(mutation_stats["deletions"] if mutation_stats else None),
            "Protected": NOT_AVAILABLE,
            "Corrected": NOT_AVAILABLE,
        },
        {
            "Metric": "Errors Detected",
            "Original": NOT_AVAILABLE,
            "Mutated": NOT_AVAILABLE,
            "Protected": cell(correction_stats["errors_detected"] if correction_stats else None),
            "Corrected": NOT_AVAILABLE,
        },
        {
            "Metric": "Errors Corrected",
            "Original": NOT_AVAILABLE,
            "Mutated": NOT_AVAILABLE,
            "Protected": NOT_AVAILABLE,
            "Corrected": cell(correction_stats["errors_corrected"] if correction_stats else None),
        },
        {
            "Metric": "Uncorrectable Errors",
            "Original": NOT_AVAILABLE,
            "Mutated": NOT_AVAILABLE,
            "Protected": NOT_AVAILABLE,
            "Corrected": cell(correction_stats["uncorrectable_errors"] if correction_stats else None),
        },
    ]

    return pd.DataFrame(rows, columns=["Metric", "Original", "Mutated", "Protected", "Corrected"])


def prepare_benchmark_chart_data(original_stats, mutation_stats, correction_stats):
    """Build a Stage/Length DataFrame for a sequence-length chart, or None.

    Reuses dna_visualization.prepare_length_comparison_data() for the
    Original/Mutated/Protected rows (no duplicated chart-prep logic),
    then appends a Corrected row when that data exists.
    """
    if original_stats is None:
        return None

    mutated_length = mutation_stats["mutated_length"] if mutation_stats else None
    protected_length = correction_stats["protected_length"] if correction_stats else None
    corrected_length = correction_stats["corrected_length"] if correction_stats else None

    chart_df = prepare_length_comparison_data(
        original_stats["dna_length"], mutated_length, protected_length
    )

    if corrected_length is not None:
        chart_df = pd.concat(
            [chart_df, pd.DataFrame([{"Stage": "Corrected DNA", "Length (bases)": corrected_length}])],
            ignore_index=True,
        )

    return chart_df


def generate_benchmark_summary(original_stats, mutation_stats, correction_stats, storage_stats) -> dict:
    """Produce short, honest conclusions from whatever data is available.

    Never claims successful recovery unless correction_stats explicitly
    reports correction_success is True.
    """
    lengths = {}
    if original_stats:
        lengths["Original"] = original_stats["dna_length"]
    if mutation_stats and mutation_stats["mutated_length"] is not None:
        lengths["Mutated"] = mutation_stats["mutated_length"]
    if correction_stats:
        if correction_stats["protected_length"] is not None:
            lengths["Protected"] = correction_stats["protected_length"]
        if correction_stats["corrected_length"] is not None:
            lengths["Corrected"] = correction_stats["corrected_length"]

    shortest_stage = None
    shortest_length = None
    if lengths:
        shortest_stage = min(lengths, key=lengths.get)
        shortest_length = lengths[shortest_stage]

    highest_overhead_percent = storage_stats["overhead_percent"] if storage_stats else None

    correction_restored_length = None
    if correction_stats and original_stats and correction_stats["corrected_length"] is not None:
        correction_restored_length = correction_stats["corrected_length"] == original_stats["dna_length"]

    recovery_confirmed = bool(correction_stats and correction_stats.get("correction_success") is True)

    return {
        "shortest_stage": shortest_stage,
        "shortest_length": shortest_length,
        "highest_overhead_percent": highest_overhead_percent,
        "correction_restored_length": correction_restored_length,
        "recovery_confirmed": recovery_confirmed,
    }


def run_benchmark(file_info: dict = None, encoding_result: dict = None, mutation_result: dict = None, correction_result: dict = None) -> dict:
    """Assemble the full benchmarking report from real, already-available data.

    This is the single entry point the UI layer calls -- it stays a
    thin wrapper over the section-level functions above.
    """
    original_stats = calculate_original_statistics(file_info, encoding_result)
    mutation_stats = calculate_mutation_comparison(mutation_result)
    correction_stats = calculate_error_correction_comparison(correction_result)

    original_length = original_stats["dna_length"] if original_stats else None
    protected_length = correction_stats["protected_length"] if correction_stats else None
    storage_stats = calculate_storage_overhead_comparison(original_length, protected_length)

    comparison_table = build_comparison_table(original_stats, mutation_stats, correction_stats)
    chart_data = prepare_benchmark_chart_data(original_stats, mutation_stats, correction_stats)
    summary = generate_benchmark_summary(original_stats, mutation_stats, correction_stats, storage_stats)

    return {
        "original_stats": original_stats,
        "mutation_stats": mutation_stats,
        "correction_stats": correction_stats,
        "storage_stats": storage_stats,
        "comparison_table": comparison_table,
        "chart_data": chart_data,
        "summary": summary,
    }
