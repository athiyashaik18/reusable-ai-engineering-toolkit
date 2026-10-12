"""Check configuration dictionaries against a simple schema.

A schema maps each required key to the type its value must have.
The validator reports every problem it finds instead of stopping
at the first one. Callers can show the list, log it, or turn it
into an exception.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConfigError:
    """One problem in a configuration dictionary.

    ``key`` is the schema entry that failed. ``message`` says what to change.
    """

    key: str
    message: str

    def __str__(self) -> str:
        return self.message


def validate_config(
    config: dict[str, Any],
    schema: dict[str, type[Any]],
) -> list[ConfigError]:
    """Return errors for missing required keys and values of the wrong type.

    Every key in ``schema`` is required. The schema value is the type that
    the configuration value must be an instance of. An empty schema has no
    required keys, so any dictionary is valid, including an empty one.

    An empty list means the configuration matches the schema. Keys that are
    not listed in the schema are ignored. Subclasses of the expected type
    are accepted, with one exception: ``bool`` is not accepted as ``int``.

    Raises:
        ValueError: ``config`` or ``schema`` is not a dictionary, a schema
            key is not a string, or a schema value is not a type.
    """
    _validate_inputs(config, schema)

    errors: list[ConfigError] = []
    for key, expected in schema.items():
        if key not in config:
            errors.append(ConfigError(key, _missing_message(key, expected)))
            continue
        value = config[key]
        if not _value_matches(value, expected):
            errors.append(ConfigError(key, _type_message(key, expected, value)))
    return errors


def _validate_inputs(config: object, schema: object) -> None:
    """Reject arguments that are not a dictionary and a type schema."""
    if not isinstance(config, dict):
        raise ValueError(
            "config must be a dictionary, "
            f"got {type(config).__name__}"
        )
    if not isinstance(schema, dict):
        raise ValueError(
            "schema must be a dictionary, "
            f"got {type(schema).__name__}"
        )

    for key, expected in schema.items():
        if not isinstance(key, str):
            raise ValueError(f"schema keys must be strings, got {key!r}")
        # list[str] and similar generics are not types. isinstance() would
        # raise TypeError later, so reject them here with a clear message.
        if not isinstance(expected, type):
            raise ValueError(
                f"schema value for {key!r} must be a type such as str or int, "
                f"got {expected!r}"
            )


def _value_matches(value: object, expected: type[Any]) -> bool:
    """Return True when value is an instance of expected.

    bool is a subclass of int, so True and False would otherwise pass an
    int check. A Boolean setting and a count are different types.
    """
    if expected is int:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, expected)


def _missing_message(key: str, expected: type[Any]) -> str:
    return f"{key} is missing. Add it with a value of type {expected.__name__}."


def _type_message(key: str, expected: type[Any], value: object) -> str:
    # Use the type name only. The value may be a secret and must not be logged.
    actual = type(value).__name__
    if expected is int and isinstance(value, bool):
        return (
            f"{key} must be an int, got bool. "
            "Booleans are not integers."
        )
    return f"{key} must be {_with_article(expected.__name__)}, got {actual}."


def _with_article(type_name: str) -> str:
    """Return ``an int`` or ``a str``, based on the type's name."""
    if type_name[:1].lower() in "aeiou":
        return f"an {type_name}"
    return f"a {type_name}"
