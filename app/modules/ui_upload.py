"""
UI module: File Upload page.

Renders the file-uploader widget, runs validation (via file_handler.py),
displays file information + a preview, and stores the result in
st.session_state so other pages/phases can access it later.
"""

import streamlit as st

from app.modules.file_handler import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    build_file_info,
    validate_uploaded_file,
)

# Key used to store the uploaded file's info dict in session state.
SESSION_KEY = "uploaded_file_info"


def render_upload() -> None:
    """Render the File Upload page."""

    st.header("📁 File Upload")
    st.write(
        "Upload a small text or image file. It will later be converted to "
        "binary and then encoded into a simulated DNA sequence in the next "
        "phase of this project."
    )
    st.caption(
        f"Allowed types: {', '.join(e.upper() for e in ALLOWED_EXTENSIONS)} "
        f"&nbsp;|&nbsp; Max size: {MAX_FILE_SIZE_MB} MB",
    )

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=list(ALLOWED_EXTENSIONS),
        accept_multiple_files=False,
    )

    # Nothing uploaded yet: show the last stored file (if any) so the
    # info doesn't disappear when the user navigates back to this page,
    # otherwise just wait for input.
    if uploaded_file is None:
        if SESSION_KEY in st.session_state:
            st.info("Showing the previously uploaded file. Upload a new one to replace it.")
            _render_file_info(st.session_state[SESSION_KEY])
        return

    result = validate_uploaded_file(uploaded_file)

    if not result.is_valid:
        st.error(f"❌ Upload failed: {result.error_message}")
        return

    file_info = build_file_info(uploaded_file)
    st.session_state[SESSION_KEY] = file_info

    st.success("✅ File uploaded successfully.")
    st.caption(
        "🔒 A content identity was recorded for this file so later pages "
        "can tell it apart from any other file with the same name."
    )
    _render_file_info(file_info)


def _render_file_info(file_info: dict) -> None:
    """Display file metadata, a preview, and basic stats as metrics."""

    st.subheader("File Information")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filename", file_info["filename"])
    col2.metric("Type", f"{file_info['category']} (.{file_info['extension']})")
    col3.metric("Size", f"{file_info['size_kb']} KB")
    col4.metric("Size (bytes)", f"{file_info['size_bytes']:,}")

    with st.expander("Preview", expanded=True):
        _render_preview(file_info)


def _render_preview(file_info: dict) -> None:
    """Show a safe, size-limited preview depending on file category."""

    category = file_info["category"]
    data = file_info["bytes"]

    if category == "Text":
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 -- fall back gracefully
            text = "(Unable to decode file as text.)"

        # Only show a limited excerpt so we never dump a huge file
        # into the page, even though the size limit is already small.
        preview_limit = 2000
        excerpt = text[:preview_limit]
        st.text_area("Text preview (first 2000 characters)", excerpt, height=200)
        if len(text) > preview_limit:
            st.caption("Preview truncated — only the first 2000 characters are shown.")

    elif category == "Image":
        st.image(data, caption=file_info["filename"], use_container_width=True)

    else:
        st.write("No preview available for this file type.")
