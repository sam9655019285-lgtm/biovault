"""
Tests for app/modules/data_export.py.

Plain-Python tests (no Streamlit). Report/metadata/CSV generation is
fully deterministic when a fixed `timestamp` is supplied.
Run with:  python -m pytest
"""

import csv
import io
import json

import pytest

from app.modules.data_export import (
    DataExportError,
    validate_export_data,
    export_dna_text,
    import_dna_text,
    export_metadata_json,
    export_analysis_csv,
    build_report_data,
    generate_text_report,
)


# 1. Valid DNA export ---------------------------------------------------------

def test_export_dna_text_valid_sequence():
    assert export_dna_text("acgtACGT") == "ACGTACGT"


# 2. Invalid DNA export rejection -----------------------------------------------

def test_export_dna_text_rejects_invalid_characters():
    with pytest.raises(DataExportError):
        export_dna_text("ACGTX")


# 3. Empty DNA rejection --------------------------------------------------------

def test_export_dna_text_rejects_empty_sequence():
    with pytest.raises(DataExportError):
        export_dna_text("")


def test_validate_export_data_rejects_non_string():
    with pytest.raises(DataExportError):
        validate_export_data(1234)  # type: ignore[arg-type]


# 4. Lowercase DNA normalization -------------------------------------------------

def test_export_dna_text_normalizes_lowercase():
    assert export_dna_text("acgt") == "ACGT"


# 5. DNA text import -------------------------------------------------------------

def test_import_dna_text_strips_surrounding_whitespace():
    assert import_dna_text("  ACGTACGT  \n") == "ACGTACGT"


def test_import_dna_text_normalizes_lowercase():
    assert import_dna_text("acgtacgt") == "ACGTACGT"


# 6. Invalid DNA import -----------------------------------------------------------

def test_import_dna_text_rejects_invalid_characters():
    with pytest.raises(DataExportError):
        import_dna_text("ACGTXYZ")


def test_import_dna_text_rejects_internal_whitespace():
    # Only surrounding whitespace is stripped; internal whitespace is an
    # invalid character, not silently removed.
    with pytest.raises(DataExportError):
        import_dna_text("ACGT ACGT")


# 7. Empty imported file -----------------------------------------------------------

def test_import_dna_text_rejects_empty_file():
    with pytest.raises(DataExportError):
        import_dna_text("")


def test_import_dna_text_rejects_whitespace_only_file():
    with pytest.raises(DataExportError):
        import_dna_text("   \n\t  ")


# 8. Metadata JSON validity -----------------------------------------------------------

def test_export_metadata_json_produces_valid_json():
    file_info = {"filename": "test.txt", "size_bytes": 100}
    encoding_result = {"dna_length": 400, "dna_sequence": "ACGT" * 100}
    metadata = export_metadata_json(file_info, encoding_result, timestamp="2026-01-01T00:00:00+00:00")
    json_text = json.dumps(metadata)
    reparsed = json.loads(json_text)
    assert reparsed["source_filename"] == "test.txt"
    assert reparsed["original_dna_length"] == 400
    assert reparsed["export_timestamp"] == "2026-01-01T00:00:00+00:00"


def test_export_metadata_json_uses_null_for_missing_values():
    metadata = export_metadata_json(timestamp="2026-01-01T00:00:00+00:00")
    json_text = json.dumps(metadata)
    assert "null" in json_text
    assert metadata["source_filename"] is None
    assert metadata["mutation_type"] is None


# 9. Metadata excludes raw file bytes ---------------------------------------------------

def test_export_metadata_json_excludes_raw_file_bytes():
    file_info = {"filename": "test.txt", "size_bytes": 5, "bytes": b"hello"}
    metadata = export_metadata_json(file_info, timestamp="2026-01-01T00:00:00+00:00")
    assert "bytes" not in metadata
    # Ensure no raw bytes value leaked into any field.
    assert b"hello" not in json.dumps(metadata, default=str).encode()


# 10. CSV generation -----------------------------------------------------------------------

def test_export_analysis_csv_produces_valid_csv():
    file_info = {"filename": "test.txt", "size_bytes": 100}
    encoding_result = {"dna_length": 400}
    csv_text = export_analysis_csv(file_info, encoding_result)
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows[0] == ["Metric", "Value"]
    assert ["Original file size (bytes)", "100"] in rows
    assert ["Original DNA length (bases)", "400"] in rows


# 11. CSV headers ------------------------------------------------------------------------------

def test_export_analysis_csv_header_row():
    csv_text = export_analysis_csv()
    first_line = csv_text.splitlines()[0]
    assert first_line == "Metric,Value"


# 12. Missing optional values --------------------------------------------------------------------

def test_export_analysis_csv_missing_values_are_blank_not_zero():
    csv_text = export_analysis_csv()  # nothing provided at all
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    for label, value in rows[1:]:
        assert value == ""  # never a fabricated "0"


def test_export_metadata_json_partial_data_only_includes_real_values():
    mutation_result = {
        "mutation_type": "substitution",
        "mutation_rate": 10,
        "seed": 42,
        "stats": {"mutated_length": 100, "total_edits": 5},
    }
    metadata = export_metadata_json(mutation_result=mutation_result, timestamp="2026-01-01T00:00:00+00:00")
    assert metadata["mutation_type"] == "substitution"
    assert metadata["mutation_seed"] == 42
    assert metadata["original_dna_length"] is None  # no encoding_result given


# 13. Report generation --------------------------------------------------------------------------

def test_generate_text_report_produces_text():
    report_data = build_report_data(timestamp="2026-01-01T00:00:00+00:00")
    report_text = generate_text_report(report_data)
    assert isinstance(report_text, str)
    assert "BIOVAULT" in report_text.upper()


# 14. Report contains required sections -----------------------------------------------------------

def test_generate_text_report_contains_all_required_sections():
    report_data = build_report_data(timestamp="2026-01-01T00:00:00+00:00")
    report_text = generate_text_report(report_data)
    required_phrases = [
        "SOURCE FILE INFORMATION",
        "DNA ENCODING SUMMARY",
        "MUTATION SIMULATION SUMMARY",
        "ERROR-CORRECTION SUMMARY",
        "STORAGE-EFFICIENCY SUMMARY",
        "VISUALIZATION SUMMARY",
        "LIMITATIONS",
        "Report generated:",
    ]
    for phrase in required_phrases:
        assert phrase in report_text


def test_generate_text_report_marks_unavailable_sections_clearly():
    report_data = build_report_data(timestamp="2026-01-01T00:00:00+00:00")
    report_text = generate_text_report(report_data)
    assert "Not available" in report_text


# 15. Exported DNA contains only A, T, G, and C -----------------------------------------------------

def test_export_dna_text_output_contains_only_valid_bases():
    result = export_dna_text("acgtACGTacgtACGT")
    assert set(result) <= {"A", "T", "G", "C"}


# 16. Imported sequence length calculation ------------------------------------------------------------

def test_imported_sequence_length_matches_input():
    sequence = "ACGT" * 25
    result = import_dna_text(sequence)
    assert len(result) == 100


# 17. Deterministic report generation when timestamp is supplied -------------------------------------------

def test_report_generation_is_deterministic_with_fixed_timestamp():
    file_info = {"filename": "demo.txt", "size_bytes": 20}
    encoding_result = {"dna_length": 80, "dna_sequence": "ACGT" * 20}
    report_data_a = build_report_data(file_info, encoding_result, timestamp="2026-01-01T00:00:00+00:00")
    report_data_b = build_report_data(file_info, encoding_result, timestamp="2026-01-01T00:00:00+00:00")
    assert generate_text_report(report_data_a) == generate_text_report(report_data_b)


def test_metadata_json_is_deterministic_with_fixed_timestamp():
    metadata_a = export_metadata_json(timestamp="2026-01-01T00:00:00+00:00")
    metadata_b = export_metadata_json(timestamp="2026-01-01T00:00:00+00:00")
    assert metadata_a == metadata_b


# Extra: full pipeline sanity check using the real encoder/mutator/correction modules -----------------

def test_full_pipeline_export_uses_real_module_data():
    from app.modules.dna_encoder import encode_file_to_dna
    from app.modules.dna_mutator import mutate_dna
    from app.modules.dna_error_correction import add_redundancy, correct_substitution_errors

    original = b"BioVault export test"
    enc = encode_file_to_dna(original)
    encoding_result = {"dna_length": enc["dna_length"], "dna_sequence": enc["dna_sequence"]}

    mutation_stats = mutate_dna(enc["dna_sequence"], "substitution", 5, seed=1)
    mutation_result = {
        "mutation_type": mutation_stats["mutation_type"],
        "mutation_rate": mutation_stats["mutation_rate"],
        "seed": mutation_stats["seed"],
        "mutated_dna_sequence": mutation_stats["mutated_sequence"],
        "stats": mutation_stats,
    }

    protection = add_redundancy(enc["dna_sequence"], block_size=4, redundancy_size=2)
    correction = correct_substitution_errors(
        protection["protected_sequence"], block_size=4, redundancy_size=2, original_length=protection["original_length"]
    )
    correction_result = {
        "block_size": 4,
        "redundancy_size": 2,
        "protected_sequence": protection["protected_sequence"],
        "correction": correction,
    }

    file_info = {"filename": "export_test.bin", "size_bytes": len(original)}

    metadata = export_metadata_json(file_info, encoding_result, mutation_result, correction_result, timestamp="2026-01-01T00:00:00+00:00")
    assert metadata["original_dna_length"] == enc["dna_length"]
    assert metadata["mutated_dna_length"] == mutation_stats["mutated_length"]
    assert metadata["protected_dna_length"] == len(protection["protected_sequence"])

    csv_text = export_analysis_csv(file_info, encoding_result, mutation_result, correction_result)
    assert "Errors detected" in csv_text
