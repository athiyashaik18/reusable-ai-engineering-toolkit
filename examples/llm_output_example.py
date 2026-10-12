"""Check fictional model replies against a field schema.

The replies are made up. This script does not call a model or read
credentials.

Run it from the project directory:

    python examples/llm_output_example.py
"""

import sys
from pathlib import Path

# Running this file as a script puts examples/ on the import path.
# Add the project root so llm_output_validator can be imported.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from llm_output_validator import validate_llm_output


def main() -> None:
    """Validate one accepted reply and one reply with field problems."""
    schema = {
        "answer": str,
        "score": int,
        "confident": bool,
    }
    accepted = validate_llm_output(
        '{"answer": "The study group met on Monday.", "score": 3, "confident": false}',
        schema,
    )
    if not accepted.is_valid or accepted.data is None:
        print("The sample response was not accepted.")
        print(accepted)
        raise SystemExit(1)
    print(f"Valid response accepted with {len(accepted.data)} fields.")

    draft = validate_llm_output(
        '{"answer": "The study group met on Monday.", "score": true}',
        schema,
    )
    print("Draft response:")
    for error in draft.errors:
        print(f"- {error.message}")


if __name__ == "__main__":
    main()
