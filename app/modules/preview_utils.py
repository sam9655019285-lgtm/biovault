"""
Shared "large-data preview" logic (non-UI, no Streamlit dependency).

Several pages display DNA sequences, binary strings, or imported text
that can be very long for medium/large files (Phase 15). Showing the
full string in the browser is slow to render and unnecessary for a
human to read, so every such page shows only a short preview instead.

IMPORTANT: this module only ever affects what is *displayed*. It never
truncates, modifies, or discards the actual stored data -- decoding,
validation, error correction, export, import, hash comparison, and file
recovery all continue to use the complete, untouched string/bytes held
in session state. Only the on-screen preview is shortened.
"""

DEFAULT_PREVIEW_LIMIT = 500

PREVIEW_NOTICE = (
    "Preview shortened for performance. The complete data remains "
    "available for processing/export."
)


def build_preview(text: str, limit: int = DEFAULT_PREVIEW_LIMIT) -> dict:
    """Return a structured preview of `text`, never modifying `text` itself.

    Always returns the same shape, whether or not truncation happened,
    so callers don't need to special-case "was it shortened?":

        {
            "preview": str,          # first `limit` characters (or all of it)
            "total_length": int,     # len(text), always the REAL total
            "shown_length": int,     # len(preview)
            "hidden_length": int,    # 0 when nothing was hidden
            "truncated": bool,
        }
    """
    if not isinstance(text, str):
        raise TypeError("build_preview() requires a string.")
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise ValueError("limit must be a non-negative whole number.")

    total_length = len(text)
    if total_length <= limit:
        return {
            "preview": text,
            "total_length": total_length,
            "shown_length": total_length,
            "hidden_length": 0,
            "truncated": False,
        }

    preview = text[:limit]
    return {
        "preview": preview,
        "total_length": total_length,
        "shown_length": len(preview),
        "hidden_length": total_length - len(preview),
        "truncated": True,
    }


def preview_caption(preview_info: dict) -> str:
    """Return a human-readable caption describing a build_preview() result.

    Returns an empty string when nothing was truncated (nothing to
    explain to the user).
    """
    if not preview_info.get("truncated"):
        return ""

    return (
        f"{PREVIEW_NOTICE} Showing {preview_info['shown_length']:,} of "
        f"{preview_info['total_length']:,} characters "
        f"({preview_info['hidden_length']:,} hidden)."
    )
