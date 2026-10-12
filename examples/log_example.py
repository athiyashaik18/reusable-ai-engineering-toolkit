"""Log fictional retrieval events with context fields.

The request id and durations are made up. This script does not read
credentials or contact an external service.

Run it from the project directory:

    python examples/log_example.py
"""

import sys
from pathlib import Path

# Running this file as a script puts examples/ on the import path.
# Add the project root so structured_logger can be imported.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from structured_logger import get_logger


def main() -> None:
    """Write two events for a fictional search."""
    logger = get_logger("notebook-helper", level="INFO")
    logger.info(
        "retrieval finished",
        operation="search",
        request_id="req-1001",
        status="ok",
        duration_ms=18,
    )
    logger.warning(
        "retrieval was slow",
        operation="search",
        request_id="req-1001",
        status="slow",
        duration_ms=900,
    )


if __name__ == "__main__":
    main()
