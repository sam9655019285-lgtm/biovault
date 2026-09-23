"""
Tests for app/modules/preview_utils.py (Phase 15).

Covers safe preview behavior for potentially very long DNA sequences,
binary strings, and imported text: only the displayed preview is ever
shortened, the reported total length is always the real one, and the
original string is never modified.
"""

import pytest

from app.modules.preview_utils import build_preview, preview_caption, DEFAULT_PREVIEW_LIMIT, PREVIEW_NOTICE


def test_short_text_is_not_truncated():
    info = build_preview("ACGT", limit=500)
    assert info["preview"] == "ACGT"
    assert info["truncated"] is False
    assert info["total_length"] == 4
    assert info["shown_length"] == 4
    assert info["hidden_length"] == 0


def test_text_exactly_at_limit_is_not_truncated():
    text = "A" * 500
    info = build_preview(text, limit=500)
    assert info["truncated"] is False
    assert info["hidden_length"] == 0


def test_long_text_is_truncated_to_limit():
    text = "A" * 10_000
    info = build_preview(text, limit=500)
    assert info["truncated"] is True
    assert len(info["preview"]) == 500
    assert info["shown_length"] == 500


def test_long_text_reports_correct_total_and_hidden_length():
    text = "A" * 10_000
    info = build_preview(text, limit=500)
    assert info["total_length"] == 10_000
    assert info["hidden_length"] == 9_500
    assert info["shown_length"] + info["hidden_length"] == info["total_length"]


def test_build_preview_never_modifies_the_original_string():
    text = "ACGT" * 5000
    original_copy = str(text)
    build_preview(text, limit=100)
    assert text == original_copy  # strings are immutable, but verify no surprises


def test_default_preview_limit_is_used_when_not_specified():
    text = "A" * (DEFAULT_PREVIEW_LIMIT + 50)
    info = build_preview(text)
    assert info["shown_length"] == DEFAULT_PREVIEW_LIMIT
    assert info["truncated"] is True


def test_empty_text_is_handled_safely():
    info = build_preview("", limit=500)
    assert info["preview"] == ""
    assert info["truncated"] is False
    assert info["total_length"] == 0


def test_build_preview_rejects_non_string_input():
    with pytest.raises(TypeError):
        build_preview(12345, limit=10)  # type: ignore[arg-type]


def test_build_preview_rejects_negative_limit():
    with pytest.raises(ValueError):
        build_preview("ACGT", limit=-1)


def test_preview_caption_empty_when_not_truncated():
    info = build_preview("ACGT", limit=500)
    assert preview_caption(info) == ""


def test_preview_caption_mentions_shown_total_and_hidden_counts():
    info = build_preview("A" * 10_000, limit=500)
    caption = preview_caption(info)
    assert PREVIEW_NOTICE in caption
    assert "500" in caption
    assert "10,000" in caption
    assert "9,500" in caption
