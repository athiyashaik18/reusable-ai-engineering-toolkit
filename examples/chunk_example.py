"""Split a fictional study-group note into character chunks.

The note is made up. This script does not read a file or call a service.

Run it from the project directory:

    python examples/chunk_example.py
"""

import sys
from pathlib import Path

# Running this file as a script puts examples/ on the import path.
# Add the project root so text_chunker can be imported.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from text_chunker import chunk_text


def main() -> None:
    """Print overlapping windows from a short fictional note."""
    document = (
        "Monday note: Ada asked how to split long notes before retrieval. "
        "Tuesday note: the study group kept punctuation and blank lines as written."
    )
    chunks = chunk_text(document, chunk_size=48, overlap=10)
    print(f"{len(chunks)} chunks")
    for number, chunk in enumerate(chunks, start=1):
        print(f"Chunk {number} ({len(chunk)} characters): {chunk!r}")


if __name__ == "__main__":
    main()
