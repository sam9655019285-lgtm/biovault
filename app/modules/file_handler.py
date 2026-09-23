"""
File handling logic (non-UI).

This module is responsible for validating uploaded files and building a
simple dictionary of file information. Keeping this separate from the
UI module (ui_upload.py) means the validation rules can be tested or
reused without touching any Streamlit code.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional

# Supported file extensions for this prototype. Kept intentionally small
# per project scope (text + common image formats only).
ALLOWED_EXTENSIONS = ("txt", "png", "jpg", "jpeg")

# Human-readable category for each allowed extension, used for display
# and for deciding how to render a preview.
EXTENSION_CATEGORY = {
    "txt": "Text",
    "png": "Image",
    "jpg": "Image",
    "jpeg": "Image",
}

MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class FileHandlerError(Exception):
    """Raised when file data given to a file_handler function is invalid."""


@dataclass
class FileValidationResult:
    """Result of validating an uploaded file.

    is_valid tells the UI whether it is safe to proceed; error_message
    holds a user-friendly explanation when is_valid is False.
    """

    is_valid: bool
    error_message: Optional[str] = None


def compute_content_hash(data: bytes) -> str:
    """Return a deterministic SHA-256 hex digest of file bytes.

    Used as a file's reliable "content identity" (Phase 14) -- unlike
    filename/size, two files can only produce the same hash if their
    bytes are actually identical, so this is what session-state
    matching relies on to tell apart two different files that happen
    to share the same filename.

    Accepts bytes/bytearray (empty bytes included -- an empty file
    still has a well-defined, stable hash). Never modifies the input.
    Raises FileHandlerError for any other input type rather than
    silently hashing something that isn't actually file content.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise FileHandlerError("Content to hash must be bytes.")

    return hashlib.sha256(bytes(data)).hexdigest()


def get_extension(filename: str) -> str:
    """Return the lowercase file extension (without the dot)."""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def validate_uploaded_file(uploaded_file) -> FileValidationResult:
    """Validate a Streamlit UploadedFile object.

    Checks performed:
    1. The upload is not empty / missing.
    2. The file extension is one we support.
    3. The file size does not exceed MAX_FILE_SIZE_BYTES.

    Any unexpected problem while reading the file is caught and turned
    into a friendly error message instead of crashing the app.
    """
    try:
        if uploaded_file is None:
            return FileValidationResult(False, "No file was uploaded.")

        # getbuffer() lets us check size without disturbing the file
        # pointer that will later be used to read the actual bytes.
        size_bytes = uploaded_file.size
        if size_bytes is None or size_bytes == 0:
            return FileValidationResult(False, "The uploaded file is empty.")

        extension = get_extension(uploaded_file.name)
        if extension not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(ext.upper() for ext in ALLOWED_EXTENSIONS)
            return FileValidationResult(
                False,
                f"Unsupported file type '.{extension or '?'}'. "
                f"Allowed types are: {allowed}.",
            )

        if size_bytes > MAX_FILE_SIZE_BYTES:
            size_mb = size_bytes / (1024 * 1024)
            return FileValidationResult(
                False,
                f"File is too large ({size_mb:.2f} MB). "
                f"Maximum allowed size is {MAX_FILE_SIZE_MB} MB.",
            )

        return FileValidationResult(True)

    except Exception as exc:  # noqa: BLE001 -- surface any unexpected error safely
        return FileValidationResult(False, f"Could not read the uploaded file ({exc}).")


def build_file_info(uploaded_file) -> dict:
    """Build a plain-dict summary of an already-validated uploaded file.

    This dict is what gets stored in st.session_state so the rest of
    the app (later phases: encoding, mutation, dashboard) can access
    file details without re-reading the raw upload widget.
    """
    extension = get_extension(uploaded_file.name)
    size_bytes = uploaded_file.size
    data = uploaded_file.getvalue()

    return {
        "filename": uploaded_file.name,
        "extension": extension,
        "category": EXTENSION_CATEGORY.get(extension, "Unknown"),
        "mime_type": uploaded_file.type,
        "size_bytes": size_bytes,
        "size_kb": round(size_bytes / 1024, 2),
        "bytes": data,
        "content_hash": compute_content_hash(data),
    }
