"""
Regression tests for app/modules/file_handler.py (Phase 2), re-checked
here to confirm later-phase changes didn't break existing upload
behavior. Also covers Phase 14's content-hash helper and file-info field.
"""

import hashlib

import pytest

from app.modules.file_handler import (
    FileHandlerError,
    build_file_info,
    compute_content_hash,
    get_extension,
    validate_uploaded_file,
)


class FakeUpload:
    def __init__(self, name, data, mime="text/plain"):
        self.name = name
        self._data = data
        self.size = len(data)
        self.type = mime

    def getvalue(self):
        return self._data


def test_valid_txt_is_accepted():
    result = validate_uploaded_file(FakeUpload("sample.txt", b"hello"))
    assert result.is_valid


def test_unsupported_extension_is_rejected():
    result = validate_uploaded_file(FakeUpload("virus.exe", b"data"))
    assert not result.is_valid


def test_oversized_file_is_rejected():
    result = validate_uploaded_file(FakeUpload("big.png", b"0" * 6 * 1024 * 1024))
    assert not result.is_valid


def test_empty_file_is_rejected():
    result = validate_uploaded_file(FakeUpload("empty.txt", b""))
    assert not result.is_valid


def test_none_upload_is_rejected():
    result = validate_uploaded_file(None)
    assert not result.is_valid


def test_get_extension_is_case_insensitive():
    assert get_extension("Photo.PNG") == "png"


# --- Phase 14: content-hash helper -------------------------------------------

def test_same_bytes_produce_the_same_hash():
    assert compute_content_hash(b"hello world") == compute_content_hash(b"hello world")


def test_different_bytes_produce_different_hashes():
    assert compute_content_hash(b"hello world") != compute_content_hash(b"hello world!")


def test_empty_bytes_produce_a_valid_deterministic_hash():
    result = compute_content_hash(b"")
    assert result == hashlib.sha256(b"").hexdigest()
    assert result == compute_content_hash(b"")


def test_hash_matches_hashlib_sha256_directly():
    data = b"BioVault content-identity test payload"
    assert compute_content_hash(data) == hashlib.sha256(data).hexdigest()


def test_hash_accepts_bytearray():
    assert compute_content_hash(bytearray(b"abc")) == compute_content_hash(b"abc")


def test_hash_does_not_modify_input_bytes():
    data = bytearray(b"do not mutate me")
    original_copy = bytes(data)
    compute_content_hash(data)
    assert data == original_copy


def test_hash_rejects_unsupported_input_type():
    with pytest.raises(FileHandlerError):
        compute_content_hash("not bytes")  # type: ignore[arg-type]

    with pytest.raises(FileHandlerError):
        compute_content_hash(None)  # type: ignore[arg-type]

    with pytest.raises(FileHandlerError):
        compute_content_hash(12345)  # type: ignore[arg-type]


# --- Phase 14: build_file_info includes a content_hash ------------------------

def test_build_file_info_includes_content_hash():
    file_info = build_file_info(FakeUpload("sample.txt", b"hello"))
    assert file_info["content_hash"] == compute_content_hash(b"hello")
    # All previously existing fields must still be present.
    assert file_info["filename"] == "sample.txt"
    assert file_info["extension"] == "txt"
    assert file_info["size_bytes"] == 5
    assert file_info["bytes"] == b"hello"


def test_build_file_info_same_filename_different_content_gives_different_hash():
    file_a = build_file_info(FakeUpload("sample.txt", b"content A"))
    file_b = build_file_info(FakeUpload("sample.txt", b"content B (different)"))

    assert file_a["filename"] == file_b["filename"]
    assert file_a["content_hash"] != file_b["content_hash"]


def test_build_file_info_same_filename_identical_content_gives_same_hash():
    file_a = build_file_info(FakeUpload("sample.txt", b"identical bytes"))
    file_b = build_file_info(FakeUpload("sample.txt", b"identical bytes"))

    assert file_a["filename"] == file_b["filename"]
    assert file_a["content_hash"] == file_b["content_hash"]
