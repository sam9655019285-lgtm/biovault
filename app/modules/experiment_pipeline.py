"""
End-to-end DNA storage experiment orchestration (non-UI, no Streamlit
dependency).

This module does not implement any new DNA-storage logic. It only
CALLS BioVault's existing, already-tested modules in sequence and
collects their real results into one structured experiment report:

    Input File -> File Identity -> DNA Encoding -> DNA Analysis
    -> Storage Analysis -> Capacity Analysis -> Redundancy
    -> Simulated Corruption -> Recovery/Error Correction
    -> Integrity Verification -> Performance Measurement
    -> Final Experiment Result

Every stage reuses the real module responsible for that concept:
- dna_encoder.py / dna_decoder.py -- the actual, unmodified encode/
  decode pipeline (never a second encoding algorithm).
- encoding_models.py -- GC/homopolymer DNA analysis.
- storage_analysis.py -- storage-efficiency math.
- capacity_analysis.py -- theoretical-vs-actual capacity math.
- redundancy_simulation.py -- whole-copy redundancy, corruption, and
  majority/agreement/error-correction recovery (Phases 18).
- dna_integrity.py -- the baseline integrity/status classification.
- performance_analysis.py -- real timing/memory measurement.
- file_handler.py / result_identity.py -- content-hash file identity.

EDUCATIONAL SIMULATION ONLY. Nothing here represents real laboratory
DNA synthesis, sequencing, or experimental biological validation.
"""

import uuid

from app.modules.dna_encoder import DNAEncodingError, encode_file_to_dna
from app.modules.dna_decoder import DNADecodingError, decode_dna_to_file
from app.modules.encoding_models import (
    EncodingModelError,
    DEFAULT_HOMOPOLYMER_THRESHOLD,
    analyze_gc_content,
    count_homopolymer_runs,
)
from app.modules.storage_analysis import StorageAnalysisError, analyze_storage_efficiency
from app.modules.capacity_analysis import (
    CapacityAnalysisError,
    compare_actual_to_theoretical,
    calculate_copy_redundancy_overhead,
)
from app.modules.redundancy_simulation import (
    RedundancySimulationError,
    RECOVERY_STRATEGY_MAJORITY,
    STATUS_RECOVERED,
    STATUS_PARTIALLY_RECOVERED,
    STATUS_FAILED,
    STATUS_UNABLE_TO_VERIFY,
    run_redundancy_simulation,
)
from app.modules.dna_integrity import DNAIntegrityError, build_integrity_report
from app.modules.performance_analysis import measure_time_and_memory
from app.modules.file_handler import compute_content_hash

# Overall experiment-status labels shown to the user. These map from
# (and never contradict) the underlying redundancy_simulation status,
# so the same "never claim success without proof" rule always applies.
EXPERIMENT_STATUS_RECOVERED = "Successfully Recovered"
EXPERIMENT_STATUS_FAILED = "Recovery Failed"
EXPERIMENT_STATUS_UNABLE_TO_VERIFY = "Unable to Verify"
EXPERIMENT_STATUS_NOT_AVAILABLE = "Simulation Completed - Recovery Not Available"

_STATUS_MAP = {
    STATUS_RECOVERED: EXPERIMENT_STATUS_RECOVERED,
    STATUS_PARTIALLY_RECOVERED: EXPERIMENT_STATUS_FAILED,
    STATUS_FAILED: EXPERIMENT_STATUS_NOT_AVAILABLE,
    STATUS_UNABLE_TO_VERIFY: EXPERIMENT_STATUS_UNABLE_TO_VERIFY,
}

STAGE_NAMES = (
    "Preparing input",
    "Encoding DNA",
    "Analyzing DNA",
    "Calculating storage",
    "Calculating capacity",
    "Applying redundancy",
    "Simulating corruption",
    "Recovering data",
    "Verifying integrity",
    "Measuring performance",
    "Building report",
)


class ExperimentPipelineError(Exception):
    """Raised when an experiment cannot be run due to invalid input."""


def run_experiment(
    data: bytes,
    source_filename: str,
    extra_copies: int = 0,
    mutation_type: str = "substitution",
    mutation_rate: float = 5.0,
    seed: int = None,
    recovery_strategy: str = RECOVERY_STRATEGY_MAJORITY,
    agreement_fraction: float = 0.5,
    homopolymer_threshold: int = DEFAULT_HOMOPOLYMER_THRESHOLD,
) -> dict:
    """Run one complete, reproducible end-to-end DNA storage experiment
    and return a single structured result dict.

    This function only orchestrates calls to existing BioVault modules
    -- it never reimplements encoding, decoding, mutation, redundancy,
    error correction, or integrity logic itself.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise ExperimentPipelineError("data must be bytes.")
    if not isinstance(source_filename, str) or len(source_filename) == 0:
        raise ExperimentPipelineError("source_filename must be a non-empty string.")

    data = bytes(data)
    experiment_id = str(uuid.uuid4())
    content_hash = compute_content_hash(data)

    # --- Stage: DNA Encoding (the real, unmodified encoder) ---------------
    try:
        (encode_result, encoding_time_seconds, encoding_peak_memory_bytes) = measure_time_and_memory(
            encode_file_to_dna, data
        )
    except DNAEncodingError as exc:
        raise ExperimentPipelineError(f"Encoding failed: {exc}") from exc

    dna_sequence = encode_result["dna_sequence"]

    # --- Stage: DNA Analysis (GC content / homopolymers, Phase 16/19) -----
    dna_analysis = None
    if dna_sequence:
        try:
            gc_stats = analyze_gc_content(dna_sequence)
            homopolymer_stats = count_homopolymer_runs(dna_sequence, homopolymer_threshold)
        except EncodingModelError as exc:
            raise ExperimentPipelineError(f"DNA analysis failed: {exc}") from exc

        dna_analysis = {
            "base_counts": gc_stats["counts"],
            "gc_percentage": gc_stats["gc_percentage"],
            "at_percentage": gc_stats["at_percentage"],
            "longest_homopolymer_run": gc_stats["longest_homopolymer_run"],
            "invalid_character_count": gc_stats["invalid_character_count"],
            "homopolymer_warning": homopolymer_stats["runs_at_or_above_threshold"] > 0,
            "homopolymer_threshold": homopolymer_threshold,
            "category": "simulation_educational_indicator",
        }

    # --- Stage: Storage Analysis (Phase 7, reused) -------------------------
    try:
        storage_report = analyze_storage_efficiency(
            file_size_bytes=len(data),
            dna_length=len(dna_sequence),
        )
    except StorageAnalysisError as exc:
        raise ExperimentPipelineError(f"Storage analysis failed: {exc}") from exc

    # --- Stage: Capacity Analysis (Phase 19, reused) ------------------------
    try:
        capacity_comparison = compare_actual_to_theoretical(len(data), len(dna_sequence))
    except CapacityAnalysisError as exc:
        raise ExperimentPipelineError(f"Capacity analysis failed: {exc}") from exc

    # --- Stage: Redundancy + Corruption + Recovery (Phase 18, reused) ------
    redundancy_result = None
    if dna_sequence:
        try:
            redundancy_result = run_redundancy_simulation(
                dna_sequence,
                original_bytes=data,
                extra_copies=extra_copies,
                mutation_type=mutation_type,
                mutation_rate=mutation_rate,
                seed=seed,
                recovery_strategy=recovery_strategy,
                agreement_fraction=agreement_fraction,
            )
        except RedundancySimulationError as exc:
            raise ExperimentPipelineError(f"Redundancy/recovery simulation failed: {exc}") from exc

    try:
        redundancy_overhead = calculate_copy_redundancy_overhead(len(dna_sequence), extra_copies)
    except CapacityAnalysisError as exc:
        raise ExperimentPipelineError(f"Redundancy overhead calculation failed: {exc}") from exc

    # --- Stage: Integrity Verification (Phase 17, baseline check) ----------
    # This checks the PLAIN encoded sequence (no corruption/redundancy)
    # decodes correctly -- a separate, honest baseline from whatever the
    # redundancy/corruption/recovery experiment above found.
    try:
        baseline_integrity = build_integrity_report(dna_sequence, original_bytes=data) if dna_sequence else None
    except DNAIntegrityError as exc:
        raise ExperimentPipelineError(f"Integrity verification failed: {exc}") from exc

    # --- Stage: Performance Measurement (Phase 15, reused) ------------------
    decoding_time_seconds = None
    decoding_peak_memory_bytes = None
    if dna_sequence:
        try:
            (_decoded, decoding_time_seconds, decoding_peak_memory_bytes) = measure_time_and_memory(
                decode_dna_to_file, dna_sequence
            )
        except DNADecodingError:
            pass  # timing is best-effort; correctness is already covered above

    performance = {
        "encoding_time_seconds": encoding_time_seconds,
        "encoding_peak_memory_bytes": encoding_peak_memory_bytes,
        "decoding_time_seconds": decoding_time_seconds,
        "decoding_peak_memory_bytes": decoding_peak_memory_bytes,
        "note": "Measured on this computer",
    }

    # --- Final status: derived strictly from actual byte comparison --------
    overall_status = _determine_overall_status(redundancy_result)

    return {
        "experiment_id": experiment_id,
        "source_filename": source_filename,
        "content_hash": content_hash,
        "file_size_bytes": len(data),
        "encoding": {
            "dna_length": len(dna_sequence),
            "theoretical_dna_length": capacity_comparison["theoretical_dna_length"],
            "encoding_overhead_percent": capacity_comparison["encoding_overhead_percent"],
            "effective_bits_per_base": capacity_comparison["effective_bits_per_base"],
        },
        "dna_analysis": dna_analysis,
        "storage_analysis": {
            "raw_efficiency_percent": storage_report["raw_efficiency_percent"],
            "capacity_info": storage_report["capacity_info"],
        },
        "capacity_analysis": capacity_comparison,
        "redundancy": {
            "extra_copies": extra_copies,
            "total_copies": redundancy_overhead["total_copies"],
            "total_dna_length": redundancy_overhead["total_dna_length"],
            "storage_overhead_percent": redundancy_overhead["overhead_percent"],
        },
        "corruption": {
            "type": mutation_type,
            "rate_percent": mutation_rate,
            "seed": seed,
            "corrupted_copy_count": redundancy_result["corrupted_copy_count"] if redundancy_result else None,
        },
        "recovery": {
            "strategy": recovery_strategy,
            "status": redundancy_result["status"] if redundancy_result else None,
            "recovery_percentage": redundancy_result["recovery_percentage"] if redundancy_result else None,
            "recovery_confirmed": redundancy_result["recovery_confirmed"] if redundancy_result else None,
            "unresolved_position_count": redundancy_result["unresolved_position_count"] if redundancy_result else None,
        },
        "integrity": {
            "baseline_status": baseline_integrity["status"] if baseline_integrity else None,
            "original_hash": redundancy_result["original_hash"] if redundancy_result else content_hash,
            "recovered_hash": redundancy_result["recovered_hash"] if redundancy_result else None,
            "hashes_match": (
                redundancy_result["original_hash"] == redundancy_result["recovered_hash"]
                if redundancy_result and redundancy_result["recovered_hash"] is not None
                else None
            ),
            "exact_byte_recovery": redundancy_result["exact_byte_recovery"] if redundancy_result else None,
        },
        "performance": performance,
        "overall_status": overall_status,
        "stage_names": STAGE_NAMES,
    }


def _determine_overall_status(redundancy_result: dict) -> str:
    """Map the redundancy/recovery simulation's honest status onto the
    experiment-level status vocabulary, never upgrading a status to
    imply more certainty than the underlying comparison actually found.
    """
    if redundancy_result is None:
        return EXPERIMENT_STATUS_UNABLE_TO_VERIFY

    if redundancy_result["status"] == STATUS_FAILED:
        recovery_detail = redundancy_result.get("recovery_detail") or {}
        if recovery_detail.get("alignment_available") is False:
            return EXPERIMENT_STATUS_NOT_AVAILABLE

    return _STATUS_MAP.get(redundancy_result["status"], EXPERIMENT_STATUS_UNABLE_TO_VERIFY)


def generate_experiment_report_text(result: dict) -> str:
    """Render a readable, research-report-style plain-text summary of
    one experiment result. Every value is read directly from `result`
    -- nothing here is hardcoded or invented.
    """
    lines = []

    def add(text: str = ""):
        lines.append(text)

    add("=" * 64)
    add("BIOVAULT DNA STORAGE EXPERIMENT REPORT")
    add("Educational simulation -- not real laboratory DNA storage.")
    add("=" * 64)
    add()
    add(f"Experiment ID: {result['experiment_id']}")
    add(f"Input File: {result['source_filename']}")
    add(f"Original Size: {result['file_size_bytes']:,} bytes")
    add()

    add("1. ENCODING (actual BioVault pipeline)")
    add("-" * 64)
    encoding = result["encoding"]
    add(f"DNA Length: {encoding['dna_length']:,} bases")
    add(f"Theoretical DNA Length: {encoding['theoretical_dna_length']:,} bases")
    add(f"Encoding Overhead: {encoding['encoding_overhead_percent']}%")
    add(f"Effective Bits/Base: {encoding['effective_bits_per_base']}")
    add()

    add("2. DNA ANALYSIS (simulation / educational indicators)")
    add("-" * 64)
    dna_analysis = result["dna_analysis"]
    if dna_analysis:
        add(f"GC Content: {dna_analysis['gc_percentage']}%")
        add(f"AT Content: {dna_analysis['at_percentage']}%")
        add(f"Longest Homopolymer Run: {dna_analysis['longest_homopolymer_run']}")
        add(f"Base Counts: {dna_analysis['base_counts']}")
    else:
        add("Not available -- the encoded DNA sequence is empty.")
    add()

    add("3. REDUNDANCY")
    add("-" * 64)
    redundancy = result["redundancy"]
    add(f"Extra Copies: {redundancy['extra_copies']} (total copies: {redundancy['total_copies']})")
    add(f"Total Stored Bases: {redundancy['total_dna_length']:,}")
    add(f"Storage Overhead: {redundancy['storage_overhead_percent']}%")
    add()

    add("4. CORRUPTION")
    add("-" * 64)
    corruption = result["corruption"]
    add(f"Type: {corruption['type']}")
    add(f"Rate: {corruption['rate_percent']}%")
    add(f"Random Seed: {corruption['seed']}")
    add(f"Corrupted Copies: {corruption['corrupted_copy_count']}")
    add()

    add("5. RECOVERY")
    add("-" * 64)
    recovery = result["recovery"]
    add(f"Strategy: {recovery['strategy']}")
    add(f"Recovery Percentage (positions resolved): {recovery['recovery_percentage']}%")
    add(f"Recovery Confirmed (exact byte match): {recovery['recovery_confirmed']}")
    add()

    add("6. INTEGRITY VERIFICATION")
    add("-" * 64)
    integrity = result["integrity"]
    add(f"Original SHA-256: {integrity['original_hash']}")
    add(f"Recovered SHA-256: {integrity['recovered_hash']}")
    add(f"Hashes Match: {integrity['hashes_match']}")
    add(f"Exact Byte Recovery: {integrity['exact_byte_recovery']}")
    add()

    add("7. PERFORMANCE (measured on this computer)")
    add("-" * 64)
    performance = result["performance"]
    add(f"Encoding Time: {performance['encoding_time_seconds']:.6f} seconds")
    if performance["decoding_time_seconds"] is not None:
        add(f"Decoding Time: {performance['decoding_time_seconds']:.6f} seconds")
    add(f"Encoding Peak Memory: {performance['encoding_peak_memory_bytes']:,} bytes")
    add()

    add("=" * 64)
    add(f"OVERALL STATUS: {result['overall_status']}")
    add("=" * 64)
    add()
    add("This report describes a SOFTWARE SIMULATION for educational")
    add("purposes. It does not represent real DNA synthesis, sequencing,")
    add("or laboratory experimental validation.")

    return "\n".join(lines)
