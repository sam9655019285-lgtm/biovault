"""
Final Dashboard / Project Summary / Presentation Mode logic (non-UI, no
Streamlit dependency).

This module does not duplicate any encoding, mutation, error-correction,
or analysis logic -- it only reads the result dictionaries already
produced by earlier phases (dna_encoder, dna_mutator,
dna_error_correction, storage_analysis, benchmarking) and arranges them
into a single dashboard summary, a progress checklist, and static
presentation content. Any metric without real source data is None (the
UI renders that as "Not available") -- nothing here is ever fabricated.
"""

APP_NAME = "BioVault"

# The application's actual page workflow (Phase 1-11), used for the
# Project Progress Overview. This describes the app's structure, not a
# claim about what the *current* user has personally done -- see
# get_experiment_status() for that.
PROJECT_STAGES = [
    "File Upload",
    "DNA Encoding",
    "DNA Decoding",
    "Mutation Simulation",
    "Error Correction",
    "Storage Analysis",
    "DNA Visualization",
    "Export & Import",
    "Benchmarking",
    "User Guide",
    "DNA Storage Capacity & Information Density",
    "DNA Storage Experiment (end-to-end)",
    "Project Showcase & Viva Preparation",
    "Environment & Setup Check",
]

TECHNOLOGIES = ["Python", "Streamlit", "NumPy", "Pandas", "CSV/JSON handling (built-in)", "Pytest"]

OBJECTIVES = [
    "Convert digital file data into DNA bases",
    "Recover the original file through decoding",
    "Simulate substitutions, insertions, and deletions",
    "Study simplified error-correction behavior",
    "Analyze storage efficiency and overhead",
    "Visualize and compare experiments",
    "Export and import experiment data",
]

LIMITATIONS = [
    "Simplified 2-bit DNA encoding, not a real biochemical storage scheme",
    "Simplified checksum-based error correction, not a production-grade error-correcting code",
    "Possible checksum collisions can make some errors uncorrectable by design",
    "Insertions/deletions cannot be corrected -- only detected as a length mismatch",
    "No real DNA synthesis or sequencing is performed",
    "No laboratory validation of any result",
    "All results depend on this project's own simulation assumptions",
]

FUTURE_IMPROVEMENTS = [
    "More advanced error-correcting codes",
    "Real DNA synthesis/sequencing integration",
    "Larger-scale benchmarking across many files",
    "User accounts and persistent databases",
    "More advanced sequence encoding methods",
    "Cloud deployment improvements",
]

PROBLEM_STATEMENT = (
    "Representing digital data as DNA-like sequences raises questions that "
    "are hard to explore just by reading about them: how do you actually "
    "map bits to bases, what happens when storage errors (substitutions, "
    "insertions, deletions) occur, and how much can a simple redundancy "
    "scheme actually recover? BioVault lets students explore these "
    "questions hands-on with a real (if simplified) working pipeline, "
    "instead of only a theoretical description."
)


def get_original_file_summary(file_info: dict = None):
    """Return original file info for the dashboard, or None if unavailable."""
    if not file_info:
        return None
    return {
        "filename": file_info.get("filename"),
        "size_bytes": file_info.get("size_bytes"),
        "category": file_info.get("category"),
    }


def get_encoding_summary(encoding_result: dict = None):
    """Return encoding info for the dashboard, or None if unavailable."""
    if not encoding_result:
        return None
    return {
        "dna_length": encoding_result.get("dna_length"),
        "binary_length_bits": encoding_result.get("binary_length_bits"),
    }


def get_mutation_summary(mutation_result: dict = None):
    """Return mutation info for the dashboard, or None if unavailable."""
    if not mutation_result:
        return None
    stats = mutation_result.get("stats") or {}
    return {
        "mutation_type": mutation_result.get("mutation_type"),
        "mutation_rate": mutation_result.get("mutation_rate"),
        "mutated_length": stats.get("mutated_length"),
        "total_edits": stats.get("total_edits"),
    }


def get_error_correction_summary(correction_result: dict = None):
    """Return error-correction info for the dashboard, or None if unavailable.

    recovery_confirmed is only True when the actual correction result
    explicitly reports correction_success is True -- never inferred.
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
        "recovery_confirmed": correction.get("correction_success") is True,
    }


def get_storage_summary(analysis_result: dict = None):
    """Return storage-efficiency info for the dashboard, or None if unavailable."""
    if not analysis_result:
        return None

    report = analysis_result.get("report") or {}
    redundancy_info = report.get("redundancy_info")

    return {
        "raw_efficiency_percent": report.get("raw_efficiency_percent"),
        "overhead_percent": redundancy_info.get("overhead_percent") if redundancy_info else None,
    }


def get_benchmarking_summary(benchmarking_result: dict = None):
    """Return a short benchmarking-availability summary, or None if unavailable."""
    if not benchmarking_result:
        return None
    benchmark = benchmarking_result.get("benchmark") or {}
    return {
        "available": True,
        "has_mutation_data": benchmark.get("mutation_stats") is not None,
        "has_correction_data": benchmark.get("correction_stats") is not None,
    }


def build_dashboard_summary(
    file_info: dict = None,
    encoding_result: dict = None,
    mutation_result: dict = None,
    correction_result: dict = None,
    analysis_result: dict = None,
    benchmarking_result: dict = None,
) -> dict:
    """Assemble the Final Dashboard's data from real, already-available results.

    Every section is None when its source data doesn't exist -- the UI
    is expected to render that as "Not available", never a fabricated
    value.
    """
    return {
        "app_name": APP_NAME,
        "file_summary": get_original_file_summary(file_info),
        "encoding_summary": get_encoding_summary(encoding_result),
        "mutation_summary": get_mutation_summary(mutation_result),
        "correction_summary": get_error_correction_summary(correction_result),
        "storage_summary": get_storage_summary(analysis_result),
        "benchmarking_summary": get_benchmarking_summary(benchmarking_result),
    }


def get_experiment_status(
    file_info: dict = None,
    encoding_result: dict = None,
    mutation_result: dict = None,
    correction_result: dict = None,
    benchmarking_result: dict = None,
) -> str:
    """Return the single most-advanced valid stage reached, as a short label.

    Only reports a stage as reached when the corresponding real result
    is actually present (already matched to the current file/DNA by the
    caller) -- never inferred or assumed.
    """
    if benchmarking_result:
        return "Benchmark available"
    if correction_result:
        return "Error-correction result available"
    if mutation_result:
        return "Mutation experiment available"
    if encoding_result:
        return "DNA encoded"
    if file_info:
        return "File uploaded but not encoded"
    return "No file uploaded"


def get_project_progress() -> list:
    """Return the application's page workflow as a plain list of stage names.

    This describes BioVault's structure (what pages exist), not a claim
    about which stages the current user has personally completed.
    """
    return list(PROJECT_STAGES)


def get_presentation_content() -> dict:
    """Return the static Presentation Mode content."""
    return {
        "title": f"{APP_NAME} - DNA Digital Data Storage and Error Simulation Platform",
        "problem_statement": PROBLEM_STATEMENT,
        "objectives": list(OBJECTIVES),
        "workflow": list(PROJECT_STAGES),
        "technologies": list(TECHNOLOGIES),
        "limitations": list(LIMITATIONS),
        "future_improvements": list(FUTURE_IMPROVEMENTS),
        "educational_significance": (
            "BioVault gives students a hands-on way to connect abstract "
            "concepts (binary representation, redundancy, error correction, "
            "storage efficiency) to a concrete, inspectable pipeline, "
            "without requiring any lab equipment or real DNA."
        ),
        "simulation_disclaimer": (
            f"{APP_NAME} is a simulation and educational platform. It is "
            "NOT a real DNA synthesis, sequencing, or laboratory storage system."
        ),
    }
