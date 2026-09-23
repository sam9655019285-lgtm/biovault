"""
Shared file-identity / staleness-matching logic (non-UI, no Streamlit
dependency).

Every downstream page (DNA Encoding, Decoding, Mutation, Error
Correction, Storage Analysis, Visualization, Export/Import,
Benchmarking, Final Dashboard) stores a "source-specific" result in
session state and, on every rerun, must decide whether that stored
result still belongs to the file currently on the File Upload page.

Before Phase 14, that check only compared filenames. Uploading a
*different* file that happened to share the same filename as a
previous upload could therefore make a stale result look current. This
module fixes that by using the file's SHA-256 content hash (see
file_handler.compute_content_hash) as the reliable identity, alongside
filename and, where relevant, a specific DNA-sequence field.

BACKWARD COMPATIBILITY: a result dict stored without a "content_hash"
key (legacy data, from before this content-hash tracking existed) is
treated as unverifiable and NEVER considered current. This deliberately
favors correctness over convenience: a legacy result with no hash could
otherwise be shown as valid for what might actually be a different
file that happens to share the same filename, which is exactly the bug
this phase fixes. A cleared/"not available" result plus a normal
re-run of that page is always safe; silently trusting unverifiable
data is not.
"""


def file_identity_matches(file_info: dict, result: dict) -> bool:
    """Return True only if `result` was produced from the exact file
    currently held in `file_info` (matching filename AND content hash).

    Returns False (never raises) for missing/incomplete data, so a
    caller can use this directly as a session-state staleness guard.
    """
    if not file_info or not result:
        return False
    if result.get("source_filename") != file_info.get("filename"):
        return False
    if "content_hash" not in result:
        return False  # legacy/unverifiable result -- never trust it
    return result.get("content_hash") == file_info.get("content_hash")


def result_matches(file_info: dict, result: dict, dna_field: str = None, dna_sequence: str = None) -> bool:
    """Return True only if `result` matches the current file identity
    and, when `dna_field` is given, its recorded DNA sequence also
    matches `dna_sequence`.

    This is the single check every page should use before treating a
    stored session-state result as current: identity match, plus an
    optional additional check that the specific DNA sequence a result
    was computed from (e.g. "original_dna_sequence") is still the one
    currently in use.
    """
    if not file_identity_matches(file_info, result):
        return False
    if dna_field is not None and result.get(dna_field) != dna_sequence:
        return False
    return True
