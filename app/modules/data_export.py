"""
DNA sequence export/import and report generation logic (non-UI, no
Streamlit dependency).

This module turns data already produced elsewhere in BioVault (Phases
3, 5, 6, 7) into downloadable text/JSON/CSV content, and validates DNA
sequences imported back in as plain text. It never invents data -- any
metric that isn't available from the results it's given is recorded as
missing (None / omitted / blank), never guessed at or defaulted to 0.

This is a computational data-management feature for this simulation
project -- it does not represent real biological DNA storage, export,
or import.
"""

import csv
import io
import json
from datetime import datetime, timezone

from app.modules.dna_encoder import BITS_TO_BASE

VALID_BASES = tuple(BITS_TO_BASE.values())  # ("A", "C", "G", "T")
VALID_BASES_SET = set(VALID_BASES)

APP_NAME = "BioVault"
PHASES_COMPLETED = list(range(1, 10))  # Phases 1-9


class DataExportError(Exception):
    """Raised when DNA data given to an export/import function is invalid."""


def validate_export_data(sequence: str) -> str:
    """Validate a DNA sequence and return it normalized to uppercase.

    Same rules used throughout BioVault: non-empty, only A/T/G/C (any
    case, normalized to uppercase). Invalid characters are rejected
    rather than silently stripped or repaired.
    """
    if not isinstance(sequence, str):
        raise DataExportError("DNA sequence must be a string.")

    if len(sequence) == 0:
        raise DataExportError("DNA sequence is empty -- nothing to export.")

    normalized = sequence.upper()
    invalid_chars = sorted(set(normalized) - VALID_BASES_SET)
    if invalid_chars:
        raise DataExportError(
            "DNA sequence contains invalid character(s): "
            f"{', '.join(repr(c) for c in invalid_chars)}. "
            "Only A, T, G, C (any case) are allowed."
        )

    return normalized


def export_dna_text(sequence: str) -> str:
    """Return a DNA sequence as plain export text (validated, uppercase,
    no surrounding whitespace, no extra formatting)."""
    return validate_export_data(sequence)


def import_dna_text(raw_text: str) -> str:
    """Validate and normalize DNA text uploaded by the user.

    Only harmless *surrounding* whitespace is removed (leading/trailing
    spaces, tabs, newlines from how a text editor saved the file) --
    anything else (internal whitespace, blank lines, non-DNA
    characters) is rejected outright rather than silently cleaned up,
    since guessing at what to remove could change the data.
    """
    if not isinstance(raw_text, str):
        raise DataExportError("Imported file content must be text.")

    stripped = raw_text.strip()
    if len(stripped) == 0:
        raise DataExportError("Imported file is empty -- no DNA sequence found.")

    return validate_export_data(stripped)


def _collect_metrics(
    file_info: dict = None,
    encoding_result: dict = None,
    mutation_result: dict = None,
    correction_result: dict = None,
    analysis_result: dict = None,
) -> dict:
    """Pull the same set of real metrics out of each phase's result dict.

    Used by export_metadata_json, export_analysis_csv, and
    build_report_data so all three always agree on what's available.
    Every value is None when its source result wasn't provided --
    never a fabricated 0 or placeholder.
    """
    metrics = {
        "source_filename": None,
        "original_file_size_bytes": None,
        "original_dna_length": None,
        "mutation_type": None,
        "mutation_rate": None,
        "mutation_seed": None,
        "mutated_dna_length": None,
        "total_simulated_edits": None,
        "error_correction_block_size": None,
        "error_correction_redundancy_size": None,
        "protected_dna_length": None,
        "errors_detected": None,
        "errors_corrected": None,
        "uncorrectable_errors": None,
        "raw_storage_efficiency_percent": None,
        "redundancy_overhead_percent": None,
    }

    if file_info:
        metrics["source_filename"] = file_info.get("filename")
        metrics["original_file_size_bytes"] = file_info.get("size_bytes")

    if encoding_result:
        metrics["original_dna_length"] = encoding_result.get("dna_length")

    if mutation_result:
        metrics["mutation_type"] = mutation_result.get("mutation_type")
        metrics["mutation_rate"] = mutation_result.get("mutation_rate")
        metrics["mutation_seed"] = mutation_result.get("seed")
        stats = mutation_result.get("stats") or {}
        metrics["mutated_dna_length"] = stats.get("mutated_length")
        metrics["total_simulated_edits"] = stats.get("total_edits")

    if correction_result:
        metrics["error_correction_block_size"] = correction_result.get("block_size")
        metrics["error_correction_redundancy_size"] = correction_result.get("redundancy_size")
        protected_sequence = correction_result.get("protected_sequence")
        if protected_sequence:
            metrics["protected_dna_length"] = len(protected_sequence)
        correction = correction_result.get("correction") or {}
        metrics["errors_detected"] = correction.get("errors_detected")
        metrics["errors_corrected"] = correction.get("errors_corrected")
        metrics["uncorrectable_errors"] = correction.get("uncorrectable_errors")

    if analysis_result:
        report = analysis_result.get("report") or {}
        metrics["raw_storage_efficiency_percent"] = report.get("raw_efficiency_percent")
        redundancy_info = report.get("redundancy_info")
        if redundancy_info:
            metrics["redundancy_overhead_percent"] = redundancy_info.get("overhead_percent")

    return metrics


def _current_timestamp() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def export_metadata_json(
    file_info: dict = None,
    encoding_result: dict = None,
    mutation_result: dict = None,
    correction_result: dict = None,
    analysis_result: dict = None,
    timestamp: str = None,
) -> dict:
    """Build a JSON-serializable metadata dict from real available results.

    Unavailable optional values are included as `null` (Python None),
    which json.dumps() renders as JSON `null` -- never a fake value.
    Raw uploaded file bytes are never included.
    """
    metrics = _collect_metrics(file_info, encoding_result, mutation_result, correction_result, analysis_result)

    return {
        "export_timestamp": timestamp or _current_timestamp(),
        "application": {"name": APP_NAME, "phases_completed": PHASES_COMPLETED},
        **metrics,
    }


def export_analysis_csv(
    file_info: dict = None,
    encoding_result: dict = None,
    mutation_result: dict = None,
    correction_result: dict = None,
    analysis_result: dict = None,
) -> str:
    """Build a CSV string (Metric,Value) from real available results.

    Missing values are written as an empty cell, never a misleading 0.
    """
    metrics = _collect_metrics(file_info, encoding_result, mutation_result, correction_result, analysis_result)

    rows = [
        ("Original file size (bytes)", metrics["original_file_size_bytes"]),
        ("Original DNA length (bases)", metrics["original_dna_length"]),
        ("Mutated DNA length (bases)", metrics["mutated_dna_length"]),
        ("Protected DNA length (bases)", metrics["protected_dna_length"]),
        ("Total simulated edits", metrics["total_simulated_edits"]),
        ("Errors detected", metrics["errors_detected"]),
        ("Errors corrected", metrics["errors_corrected"]),
        ("Uncorrectable errors", metrics["uncorrectable_errors"]),
        ("Raw theoretical efficiency (%)", metrics["raw_storage_efficiency_percent"]),
        ("Redundancy overhead (%)", metrics["redundancy_overhead_percent"]),
    ]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Metric", "Value"])
    for label, value in rows:
        writer.writerow([label, "" if value is None else value])

    return buffer.getvalue()


def build_report_data(
    file_info: dict = None,
    encoding_result: dict = None,
    mutation_result: dict = None,
    correction_result: dict = None,
    analysis_result: dict = None,
    timestamp: str = None,
) -> dict:
    """Assemble everything generate_text_report() needs into one dict.

    Keeps section presence explicit (True/False) so the report can
    clearly say "not available" instead of omitting a section silently.
    """
    metrics = _collect_metrics(file_info, encoding_result, mutation_result, correction_result, analysis_result)

    base_counts = None
    if encoding_result and encoding_result.get("dna_sequence"):
        from app.modules.dna_visualization import count_dna_bases  # local import avoids a hard UI-adjacent dependency at module load time

        base_counts = count_dna_bases(encoding_result["dna_sequence"])

    correction_message = None
    if correction_result:
        correction_message = (correction_result.get("correction") or {}).get("message")

    return {
        "timestamp": timestamp or _current_timestamp(),
        "metrics": metrics,
        "base_counts": base_counts,
        "correction_message": correction_message,
        "sections_available": {
            "file": file_info is not None,
            "encoding": encoding_result is not None,
            "mutation": mutation_result is not None,
            "correction": correction_result is not None,
            "analysis": analysis_result is not None,
        },
    }


def generate_text_report(report_data: dict) -> str:
    """Render a readable plain-text BioVault report from build_report_data()'s output."""
    metrics = report_data["metrics"]
    available = report_data["sections_available"]
    lines = []

    def add_line(text: str = ""):
        lines.append(text)

    def value_or_unavailable(value, suffix: str = ""):
        return f"{value}{suffix}" if value is not None else "Not available"

    add_line("=" * 60)
    add_line(f"{APP_NAME} PROJECT REPORT")
    add_line("DNA Digital Data Storage and Error Simulation Platform")
    add_line("=" * 60)
    add_line()
    add_line("This report describes a SOFTWARE SIMULATION. It does not")
    add_line("represent real DNA synthesis, sequencing, or laboratory work.")
    add_line()

    add_line("1. SOURCE FILE INFORMATION")
    add_line("-" * 60)
    if available["file"]:
        add_line(f"Filename: {metrics['source_filename']}")
        add_line(f"File size: {value_or_unavailable(metrics['original_file_size_bytes'], ' bytes')}")
    else:
        add_line("Not available -- no file has been uploaded.")
    add_line()

    add_line("2. DNA ENCODING SUMMARY")
    add_line("-" * 60)
    if available["encoding"]:
        add_line(f"Original DNA length: {metrics['original_dna_length']} bases")
        if report_data["base_counts"]:
            counts = report_data["base_counts"]
            add_line(f"Base composition: A={counts['A']}, T={counts['T']}, G={counts['G']}, C={counts['C']}")
    else:
        add_line("Not available -- no DNA sequence has been encoded.")
    add_line()

    add_line("3. MUTATION SIMULATION SUMMARY")
    add_line("-" * 60)
    if available["mutation"]:
        add_line(f"Mutation type: {metrics['mutation_type']}")
        add_line(f"Mutation rate: {metrics['mutation_rate']}%")
        add_line(f"Random seed: {value_or_unavailable(metrics['mutation_seed'])}")
        add_line(f"Mutated DNA length: {metrics['mutated_dna_length']} bases")
        add_line(f"Total simulated edits: {metrics['total_simulated_edits']}")
    else:
        add_line("Not available -- no mutation has been simulated.")
    add_line()

    add_line("4. ERROR-CORRECTION SUMMARY")
    add_line("-" * 60)
    if available["correction"]:
        add_line(f"Block size: {value_or_unavailable(metrics['error_correction_block_size'])}")
        add_line(f"Redundancy size: {value_or_unavailable(metrics['error_correction_redundancy_size'])}")
        add_line(f"Protected DNA length: {value_or_unavailable(metrics['protected_dna_length'], ' bases')}")
        add_line(f"Errors detected: {value_or_unavailable(metrics['errors_detected'])}")
        add_line(f"Errors corrected: {value_or_unavailable(metrics['errors_corrected'])}")
        add_line(f"Uncorrectable errors: {value_or_unavailable(metrics['uncorrectable_errors'])}")
        if report_data["correction_message"]:
            add_line(f"Result: {report_data['correction_message']}")
        add_line("(Simplified educational checksum method -- not production-grade.)")
    else:
        add_line("Not available -- no error correction has been run.")
    add_line()

    add_line("5. STORAGE-EFFICIENCY SUMMARY")
    add_line("-" * 60)
    if available["analysis"]:
        add_line(f"Raw theoretical efficiency: {value_or_unavailable(metrics['raw_storage_efficiency_percent'], '%')}")
        add_line(f"Redundancy overhead: {value_or_unavailable(metrics['redundancy_overhead_percent'], '%')}")
    else:
        add_line("Not available -- no storage analysis has been run.")
    add_line()

    add_line("6. VISUALIZATION SUMMARY")
    add_line("-" * 60)
    if report_data["base_counts"]:
        counts = report_data["base_counts"]
        add_line(f"Total bases visualized: {counts['total']}")
        add_line("See the DNA Visualization page for full interactive charts.")
    else:
        add_line("Not available -- no DNA sequence has been encoded.")
    add_line()

    add_line("7. LIMITATIONS")
    add_line("-" * 60)
    add_line("- This is an educational software simulation, not real biology.")
    add_line("- DNA synthesis and sequencing costs are not modeled.")
    add_line("- Error correction uses a simplified, limited checksum method.")
    add_line("- Storage efficiency figures are theoretical computational estimates.")
    add_line()

    add_line("=" * 60)
    add_line(f"Report generated: {report_data['timestamp']}")
    add_line("=" * 60)

    return "\n".join(lines)
