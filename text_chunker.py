"""Split text into character windows for retrieval and prompting.

This first version counts Python characters. It does not tokenize text
and it does not call an external service.
"""


def chunk_text(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """Split ``text`` into chunks of at most ``chunk_size`` characters.

    Each later chunk starts ``chunk_size - overlap`` characters after the
    previous one. With ``chunk_size=4`` and ``overlap=1``, the windows are
    characters 0–4, then 3–7, then 6–10, and so on.

    The chunk that first reaches the end of ``text`` is the last chunk.
    A short final window keeps the remaining characters. Nothing is stripped.

    An empty string has no chunks. Text that already fits in one window is
    returned as a single chunk.

    Raises:
        ValueError: ``text`` is not a string, ``chunk_size`` is not an
            integer greater than or equal to 1, or ``overlap`` is not an
            integer in the range ``0 <= overlap < chunk_size``.
    """
    _validate_settings(text, chunk_size, overlap)
    if text == "":
        return []

    # overlap < chunk_size, so this step is at least 1 and the start
    # index cannot stay in place.
    step = chunk_size - overlap
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= length:
            break
        start += step
    return chunks


def _validate_settings(text: object, chunk_size: object, overlap: object) -> None:
    """Reject settings that would drop text or repeat the same window."""
    if not isinstance(text, str):
        raise ValueError(f"text must be a string, got {type(text).__name__}")

    # bool is a subclass of int, so True would otherwise pass an int check.
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int):
        raise ValueError(
            "chunk_size must be an integer greater than or equal to 1, "
            f"got {chunk_size!r}"
        )
    if chunk_size < 1:
        raise ValueError(
            "chunk_size must be greater than or equal to 1, "
            f"got {chunk_size!r}"
        )

    if isinstance(overlap, bool) or not isinstance(overlap, int):
        raise ValueError(
            "overlap must be an integer greater than or equal to 0, "
            f"got {overlap!r}"
        )
    if overlap < 0:
        raise ValueError(
            "overlap must be greater than or equal to 0, "
            f"got {overlap!r}"
        )
    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size, "
            f"got overlap {overlap} and chunk_size {chunk_size}"
        )
