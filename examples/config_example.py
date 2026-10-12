"""Check fictional application settings.

These values are made up. The script does not read credentials or
contact an external service.

Run it from the project directory:

    python examples/config_example.py
"""

import sys
from pathlib import Path

# Running this file as a script puts examples/ on the import path.
# Add the project root so config_validator can be imported.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config_validator import validate_config


def main() -> None:
    """Validate one accepted settings dictionary and one draft with problems."""
    schema = {
        "app_name": str,
        "max_retries": int,
        "temperature": float,
        "debug": bool,
    }
    accepted = validate_config(
        {
            "app_name": "notebook-helper",
            "max_retries": 3,
            "temperature": 0.2,
            "debug": False,
        },
        schema,
    )
    if accepted:
        print("The sample settings were not accepted.")
        for error in accepted:
            print(f"- {error.message}")
        raise SystemExit(1)
    print("Valid settings accepted.")

    draft_errors = validate_config(
        {
            "app_name": "notebook-helper",
            "max_retries": True,
            "temperature": "high",
        },
        schema,
    )
    print("Draft settings:")
    for error in draft_errors:
        print(f"- {error.message}")


if __name__ == "__main__":
    main()
