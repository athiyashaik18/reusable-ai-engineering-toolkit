"""Run a simulated call that fails twice, then succeeds.

The failure is local. This script does not call an API or read credentials.

Run it from the project directory:

    python examples/retry_example.py
"""

import sys
from pathlib import Path

# Running this file as a script puts examples/ on the import path.
# Add the project root so retry_utils can be imported.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from retry_utils import retry


class TemporaryOutage:
    """Stand-in for a retrieval call that fails a fixed number of times."""

    def __init__(self, failures_before_success: int) -> None:
        self.failures_before_success = failures_before_success
        self.attempts = 0

    def __call__(self) -> str:
        self.attempts += 1
        if self.attempts <= self.failures_before_success:
            print(f"Attempt {self.attempts}: temporary failure")
            raise ConnectionError("service unavailable")
        print(f"Attempt {self.attempts}: success")
        return "retrieved document"


def main() -> None:
    """Retry the simulated outage and print the successful result."""
    operation = TemporaryOutage(failures_before_success=2)
    result = retry(
        operation,
        retry_on=(ConnectionError,),
        max_attempts=4,
        initial_delay=0.1,
        backoff_factor=2.0,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
