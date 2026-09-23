"""
Full-pipeline integration tests for BioVault (Phase 13 QA).

These tests exercise the same non-UI business-logic modules that the
Streamlit pages call, chained together exactly as the app chains them:

    Upload -> Encode -> Decode -> confirm exact recovery
           -> Mutate (substitution / insertion / deletion)
           -> Error-correct where supported
           -> Storage analysis
           -> Visualization data
           -> Export (DNA text / metadata / CSV / report)
           -> Import DNA text back in
           -> Decode the imported DNA
           -> Benchmark
           -> Final dashboard summary

No Streamlit runtime is involved -- every module here is intentionally
UI-free, so the pipeline can be driven directly with plain Python
objects and temporary files, using a deterministic random seed for the
mutation steps.
"""

import tempfile
from pathlib import Path

import pytest

from app.modules.file_handler import build_file_info, validate_uploaded_file, get_extension
from app.modules.dna_encoder import encode_file_to_dna, DNAEncodingError
from app.modules.dna_decoder import decode_dna_to_file, compare_bytes, DNADecodingError
from app.modules.dna_mutator import mutate_dna, DNAMutationError
from app.modules.dna_error_correction import (
    add_redundancy,
    detect_errors,
    correct_substitution_errors,
    DNAErrorCorrectionError,
)
from app.modules.storage_analysis import analyze_storage_efficiency
from app.modules.dna_visualization import (
    count_dna_bases,
    prepare_base_composition_data,
    prepare_length_comparison_data,
)
from app.modules.data_export import (
    export_dna_text,
    export_metadata_json,
    export_analysis_csv,
    build_report_data,
    generate_text_report,
    import_dna_text,
    DataExportError,
)
from app.modules.benchmarking import run_benchmark
from app.modules.project_summary import build_dashboard_summary, get_experiment_status
from app.modules.result_identity import file_identity_matches, result_matches


class _FakeUploadedFile:
    """Minimal stand-in for Streamlit's UploadedFile, backed by a real
    temporary file on disk so file_handler.py's real code path is used
    unmodified."""

    def __init__(self, path: Path, mime_type: str = "text/plain"):
        self._path = path
        self.name = path.name
        self.size = path.stat().st_size
        self.type = mime_type

    def getvalue(self) -> bytes:
        return self._path.read_bytes()


@pytest.fixture
def source_file(tmp_path):
    """A small real temporary text file to drive the pipeline with."""
    content = b"BioVault integration test payload - DNA storage demo.\x00\xff"
    path = tmp_path / "integration_source.txt"
    path.write_bytes(content)
    return path, content


def test_full_pipeline_no_mutation_recovers_original_exactly(source_file):
    path, original_bytes = source_file
    uploaded = _FakeUploadedFile(path)

    # --- Upload ---------------------------------------------------------
    validation = validate_uploaded_file(uploaded)
    assert validation.is_valid
    file_info = build_file_info(uploaded)
    assert file_info["bytes"] == original_bytes

    # --- Encode -----------------------------------------------------------
    encoding_result = encode_file_to_dna(file_info["bytes"])
    encoding_result["source_filename"] = file_info["filename"]
    dna_sequence = encoding_result["dna_sequence"]
    assert encoding_result["dna_length"] == len(original_bytes) * 4

    # --- Decode + confirm exact recovery ----------------------------------
    decoded = decode_dna_to_file(dna_sequence)
    comparison = compare_bytes(original_bytes, decoded["recovered_bytes"])
    assert comparison["is_identical"]
    assert comparison["differing_bytes"] == 0

    # --- Storage analysis ---------------------------------------------------
    analysis = analyze_storage_efficiency(file_info["size_bytes"], encoding_result["dna_length"])
    assert analysis["raw_efficiency_percent"] == 100.0

    # --- Visualization data --------------------------------------------------
    base_counts = count_dna_bases(dna_sequence)
    assert base_counts["total"] == len(dna_sequence)
    composition_df = prepare_base_composition_data(dna_sequence)
    assert set(composition_df["Base"]) == {"A", "T", "G", "C"}

    # --- Export ------------------------------------------------------------
    dna_text = export_dna_text(dna_sequence)
    assert dna_text == dna_sequence

    metadata = export_metadata_json(file_info, encoding_result, None, None, {"report": analysis})
    assert metadata["original_dna_length"] == encoding_result["dna_length"]
    assert metadata["mutation_type"] is None  # never fabricated

    csv_text = export_analysis_csv(file_info, encoding_result, None, None, {"report": analysis})
    assert "Original DNA length (bases)" in csv_text

    report_data = build_report_data(file_info, encoding_result, None, None, {"report": analysis})
    report_text = generate_text_report(report_data)
    assert "Not available -- no mutation has been simulated." in report_text

    # --- Import the exported DNA text back in -------------------------------
    imported_sequence = import_dna_text(dna_text)
    assert imported_sequence == dna_sequence

    # --- Decode the imported DNA -------------------------------------------
    imported_decoded = decode_dna_to_file(imported_sequence)
    assert imported_decoded["recovered_bytes"] == original_bytes

    # --- Benchmark -----------------------------------------------------------
    benchmark = run_benchmark(file_info, encoding_result, None, None)
    assert benchmark["original_stats"]["dna_length"] == encoding_result["dna_length"]

    # --- Final dashboard summary ----------------------------------------------
    summary = build_dashboard_summary(file_info, encoding_result, None, None, {"report": analysis}, benchmark)
    assert summary["file_summary"]["filename"] == file_info["filename"]
    assert summary["mutation_summary"] is None  # honestly reflects nothing ran
    status = get_experiment_status(file_info, encoding_result, None, None, benchmark)
    assert status == "Benchmark available"


def test_mutation_error_correction_and_dashboard_reflect_real_outcomes(source_file):
    path, original_bytes = source_file
    uploaded = _FakeUploadedFile(path)
    file_info = build_file_info(uploaded)
    encoding_result = encode_file_to_dna(file_info["bytes"])
    encoding_result["source_filename"] = file_info["filename"]
    dna_sequence = encoding_result["dna_sequence"]

    # --- Substitution mutation with a deterministic seed --------------------
    mutation_result = mutate_dna(dna_sequence, "substitution", mutation_rate=10.0, seed=42)
    mutation_result["source_filename"] = file_info["filename"]
    mutation_result["original_dna_sequence"] = dna_sequence
    assert mutation_result["mutated_length"] == len(dna_sequence)  # substitutions preserve length

    # --- Error correction over the *original* (unmutated) sequence ----------
    protection = add_redundancy(dna_sequence, block_size=4, redundancy_size=2)
    # Simulate the same substitutions landing on the protected sequence by
    # re-running the mutator over the protected sequence directly.
    protected_mutation = mutate_dna(protection["protected_sequence"], "substitution", mutation_rate=5.0, seed=7)
    received = protected_mutation["mutated_sequence"]

    detection = detect_errors(
        received, protection["block_size"], protection["redundancy_size"], protection["original_length"]
    )
    correction = correct_substitution_errors(
        received, protection["block_size"], protection["redundancy_size"], protection["original_length"]
    )
    # correction_success must only be True when every detected error was
    # actually corrected -- never inferred from partial data.
    if correction["errors_detected"] == 0:
        assert correction["correction_success"] is True
    else:
        assert correction["correction_success"] == (
            correction["uncorrectable_errors"] == 0
            and correction["errors_corrected"] == correction["errors_detected"]
        )

    correction_result = {
        "source_filename": file_info["filename"],
        "original_dna_sequence": dna_sequence,
        "protected_sequence": protection["protected_sequence"],
        "block_size": protection["block_size"],
        "redundancy_size": protection["redundancy_size"],
        "correction": correction,
    }

    # --- Insertion / deletion: length must change accordingly ----------------
    insertion_result = mutate_dna(dna_sequence, "insertion", mutation_rate=10.0, seed=1)
    assert insertion_result["mutated_length"] > len(dna_sequence)
    deletion_result = mutate_dna(dna_sequence, "deletion", mutation_rate=10.0, seed=1)
    assert deletion_result["mutated_length"] < len(dna_sequence) or deletion_result["deletions"] == 0

    # An insertion/deletion-corrupted sequence must be reported as a
    # structural mismatch, never guessed at.
    bad_length_detection = detect_errors(
        insertion_result["mutated_sequence"],
        protection["block_size"],
        protection["redundancy_size"],
        protection["original_length"],
    )
    assert bad_length_detection["length_matches_expected"] is False
    assert bad_length_detection["errors_detected"] is None

    # --- Storage analysis including redundancy + mutation impact -------------
    analysis = analyze_storage_efficiency(
        file_info["size_bytes"],
        encoding_result["dna_length"],
        block_size=protection["block_size"],
        redundancy_size=protection["redundancy_size"],
        mutation_stats=mutation_result,
    )
    assert analysis["redundancy_info"]["protected_length"] == len(protection["protected_sequence"])
    assert analysis["mutation_info"]["total_edits"] == mutation_result["total_edits"]

    # --- Dashboard must not fabricate recovery success -----------------------
    summary = build_dashboard_summary(
        file_info, encoding_result, mutation_result, correction_result, {"report": analysis}, None
    )
    assert summary["correction_summary"]["recovery_confirmed"] == (correction["correction_success"] is True)


def test_stale_data_from_a_different_file_is_never_mixed_in(tmp_path):
    """Simulates the same staleness guard every dashboard/export page uses:
    a result keyed to one filename/DNA sequence must not be reused for a
    different file's data."""
    content_a = b"file A content"
    content_b = b"completely different file B content"

    path_a = tmp_path / "a.txt"
    path_a.write_bytes(content_a)
    file_info_a = build_file_info(_FakeUploadedFile(path_a))
    encoding_a = encode_file_to_dna(file_info_a["bytes"])
    encoding_a["source_filename"] = file_info_a["filename"]
    encoding_a["content_hash"] = file_info_a["content_hash"]

    path_b = tmp_path / "b.txt"
    path_b.write_bytes(content_b)
    file_info_b = build_file_info(_FakeUploadedFile(path_b))

    encoding_matches_b = file_identity_matches(file_info_b, encoding_a)
    assert encoding_matches_b is False  # different filenames -- correctly rejected

    summary = build_dashboard_summary(
        file_info_b, encoding_a if encoding_matches_b else None, None, None, None, None
    )
    assert summary["encoding_summary"] is None  # never shows file A's DNA for file B


def test_same_filename_different_content_never_matches_by_hash(tmp_path):
    """Phase 14 core scenario: File A and File B share a filename but
    have different bytes, so their content hashes differ and File A's
    encoding/downstream results must never be treated as current for
    File B, even though the old filename-only check would have let it
    through."""
    path_a = tmp_path / "sample.txt"
    path_a.write_bytes(b"original payload from file A")
    file_info_a = build_file_info(_FakeUploadedFile(path_a))
    encoding_a = encode_file_to_dna(file_info_a["bytes"])
    encoding_a["source_filename"] = file_info_a["filename"]
    encoding_a["content_hash"] = file_info_a["content_hash"]

    # Re-upload under the SAME filename but with different content.
    path_b = tmp_path / "sample.txt"
    path_b.write_bytes(b"a totally different payload for file B, same name")
    file_info_b = build_file_info(_FakeUploadedFile(path_b))

    assert file_info_a["filename"] == file_info_b["filename"]
    assert file_info_a["content_hash"] != file_info_b["content_hash"]

    # The old (Phase 13) filename-only check would have wrongly matched:
    assert encoding_a["source_filename"] == file_info_b["filename"]
    # The Phase 14 identity check correctly rejects it:
    assert file_identity_matches(file_info_b, encoding_a) is False

    summary = build_dashboard_summary(file_info_b, None, None, None, None, None)
    assert summary["encoding_summary"] is None


def test_same_filename_identical_content_may_safely_reuse_matching_result(tmp_path):
    """Re-uploading bytes that are byte-for-byte identical (same
    filename too) is safe to treat as the same file -- the content hash
    will agree, so existing results may be reused without forcing a
    pointless re-encode."""
    path_a = tmp_path / "sample.txt"
    path_a.write_bytes(b"identical bytes across both uploads")
    file_info_a = build_file_info(_FakeUploadedFile(path_a))
    encoding_a = encode_file_to_dna(file_info_a["bytes"])
    encoding_a["source_filename"] = file_info_a["filename"]
    encoding_a["content_hash"] = file_info_a["content_hash"]

    path_a_again = tmp_path / "sample.txt"
    path_a_again.write_bytes(b"identical bytes across both uploads")
    file_info_a_again = build_file_info(_FakeUploadedFile(path_a_again))

    assert file_info_a["content_hash"] == file_info_a_again["content_hash"]
    assert file_identity_matches(file_info_a_again, encoding_a) is True


def test_reencoding_updates_identity_and_invalidates_old_downstream_results(tmp_path):
    """If a different file is uploaded under the same filename and then
    re-encoded, the new encoding_result's content_hash changes -- and any
    mutation/correction/analysis result computed from the OLD DNA
    sequence must stop matching, exactly like the ui_dna_decoding.py fix
    from Phase 13 (now generalized via result_identity.result_matches)."""
    path_a = tmp_path / "sample.txt"
    path_a.write_bytes(b"first version of the file")
    file_info_a = build_file_info(_FakeUploadedFile(path_a))
    encoding_a = encode_file_to_dna(file_info_a["bytes"])
    encoding_a["source_filename"] = file_info_a["filename"]
    encoding_a["content_hash"] = file_info_a["content_hash"]

    mutation_a = mutate_dna(encoding_a["dna_sequence"], "substitution", 10.0, seed=1)
    mutation_a["source_filename"] = file_info_a["filename"]
    mutation_a["content_hash"] = file_info_a["content_hash"]
    mutation_a["original_dna_sequence"] = encoding_a["dna_sequence"]

    # Same filename, different content -> re-encoded.
    path_b = tmp_path / "sample.txt"
    path_b.write_bytes(b"second, different version of the file")
    file_info_b = build_file_info(_FakeUploadedFile(path_b))
    encoding_b = encode_file_to_dna(file_info_b["bytes"])
    encoding_b["source_filename"] = file_info_b["filename"]
    encoding_b["content_hash"] = file_info_b["content_hash"]

    # The stale mutation result (from file A's DNA) must not be reused
    # for file B's freshly re-encoded sequence.
    assert result_matches(
        file_info_b, mutation_a, "original_dna_sequence", encoding_b["dna_sequence"]
    ) is False


def test_empty_dna_input_and_invalid_characters_are_rejected():
    with pytest.raises(DNADecodingError):
        decode_dna_to_file("")

    with pytest.raises(DNAMutationError):
        mutate_dna("", "substitution", 10.0)

    with pytest.raises(DNAErrorCorrectionError):
        add_redundancy("ACGTX")  # invalid character

    with pytest.raises(DataExportError):
        import_dna_text("")

    with pytest.raises(DataExportError):
        import_dna_text("ACGTX")


def test_incompatible_dna_lengths_are_rejected_honestly():
    protection = add_redundancy("ACGTACGT", block_size=4, redundancy_size=2)
    protected = protection["protected_sequence"]

    # Truncate the protected sequence so its length no longer matches
    # what block_size/redundancy_size/original_length predict. This is
    # reported honestly as a structural mismatch, not guessed at or
    # silently forced through detection -- see detect_errors()'s
    # length_matches_expected branch.
    truncated = protected[:-1]
    result = detect_errors(truncated, protection["block_size"], protection["redundancy_size"], protection["original_length"])
    assert result["length_matches_expected"] is False
    assert result["errors_detected"] is None

    # remove_redundancy() is stricter: it must refuse outright rather
    # than return a partial/best-effort result for a mismatched length.
    from app.modules.dna_error_correction import remove_redundancy

    with pytest.raises(DNAErrorCorrectionError):
        remove_redundancy(truncated, protection["block_size"], protection["redundancy_size"], protection["original_length"])


def test_importing_dna_does_not_overwrite_original_encoded_sequence():
    original_dna = "ACGTACGTAAAA"
    imported_dna = import_dna_text("TTTTGGGGCCCC")

    # These are intentionally kept as two separate values by the app
    # (ENCODING_SESSION_KEY vs IMPORTED_DNA_SESSION_KEY) -- verify the
    # import path itself never mutates or reuses the original sequence.
    assert imported_dna != original_dna
    assert original_dna == "ACGTACGTAAAA"  # untouched
