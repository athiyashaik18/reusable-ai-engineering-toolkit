"""Tests for character-based text chunking.

The samples are fictional notes. They do not read files or call a service.
"""

from typing import Any

import pytest

from text_chunker import chunk_text


def test_normal_text_splits_without_dropping_characters() -> None:
    text = "Ada asked three questions."
    chunks = chunk_text(text, chunk_size=10, overlap=0)

    assert chunks == ["Ada asked ", "three ques", "tions."]
    assert "".join(chunks) == text
    assert all(len(chunk) <= 10 for chunk in chunks)


def test_empty_string_returns_no_chunks() -> None:
    assert chunk_text("", chunk_size=5) == []


def test_short_text_is_one_chunk() -> None:
    assert chunk_text("hi", chunk_size=10) == ["hi"]


def test_exact_chunk_boundaries() -> None:
    assert chunk_text("abcd", chunk_size=4, overlap=0) == ["abcd"]
    assert chunk_text("abcd", chunk_size=2, overlap=0) == ["ab", "cd"]
    assert chunk_text("abcde", chunk_size=2, overlap=0) == ["ab", "cd", "e"]


def test_overlap_repeats_the_shared_characters() -> None:
    chunks = chunk_text("abcdefghij", chunk_size=4, overlap=1)

    assert chunks == ["abcd", "defg", "ghij"]
    assert chunks[0][-1] == chunks[1][0]
    assert chunks[1][-1] == chunks[2][0]


def test_exact_length_with_overlap_returns_one_chunk() -> None:
    assert chunk_text("abcd", chunk_size=4, overlap=3) == ["abcd"]


def test_preserves_whitespace_and_punctuation() -> None:
    text = "a \n b."
    chunks = chunk_text(text, chunk_size=3, overlap=0)

    assert chunks == ["a \n", " b."]
    assert "".join(chunks) == text


def test_whitespace_only_text_is_preserved() -> None:
    text = "  \n"
    assert chunk_text(text, chunk_size=10) == ["  \n"]


@pytest.mark.parametrize(
    ("chunk_size", "overlap", "message"),
    [
        (0, 0, "chunk_size"),
        (-1, 0, "chunk_size"),
        (True, 0, "chunk_size"),
        (4.5, 0, "chunk_size"),
        (4, -1, "overlap"),
        (4, 4, "smaller than chunk_size"),
        (4, 5, "smaller than chunk_size"),
        (4, True, "overlap"),
        (4, False, "overlap"),
    ],
)
def test_invalid_settings_raise_value_error(
    chunk_size: object,
    overlap: object,
    message: str,
) -> None:
    notes = "sk-live-DO-NOT-LEAK-notes"
    with pytest.raises(ValueError, match=message) as caught:
        chunk_text(notes, chunk_size, overlap)  # type: ignore[arg-type]

    assert notes not in str(caught.value)


def test_text_must_be_a_string() -> None:
    notes: Any = ["not", "a", "string"]
    with pytest.raises(ValueError, match="text must be a string"):
        chunk_text(notes, chunk_size=4)
