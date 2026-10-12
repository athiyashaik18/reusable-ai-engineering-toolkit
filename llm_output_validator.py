"""Validate a model's JSON text against a simple field schema.

The response is parsed with the standard-library json module. Field
checks follow the same rules as the configuration validator: every
schema key is required, and a Boolean is not an integer. Error text
names fields and types only, because a model response may be untrusted.
"""

import json
from dataclasses import dataclass
from typing import Any

from config_validator import validate_config


@dataclass(frozen=True)
class OutputError:
    """One problem in a model response.

    ``field`` is the schema key that failed. It is ``None`` when the
    problem is the whole response, such as malformed JSON. ``message``
    does not include the response text or the field's value.
    """

    message: str
    field: str | None = None

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class ValidationResult:
    """The outcome of checking one model response.

    ``is_valid`` is true when ``errors`` is empty. ``data`` is the parsed
    object only when the response is valid. Printing the result lists the
    error messages and does not include parsed values.
    """

    errors: tuple[OutputError, ...]
    data: dict[str, Any] | None = None

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def __str__(self) -> str:
        if self.is_valid:
            return "Validation succeeded."
        return "\n".join(error.message for error in self.errors)

    def __repr__(self) -> str:
        messages = [error.message for error in self.errors]
        return f"ValidationResult(is_valid={self.is_valid}, errors={messages!r})"


def validate_llm_output(
    response: str,
    schema: dict[str, type[Any]],
) -> ValidationResult:
    """Check ``response`` as a JSON object with the required fields.

    ``schema`` maps each required field name to one Python type, such as
    ``str``, ``int``, ``float``, ``bool``, ``list``, or ``dict``. The
    top-level JSON value must be an object. Extra fields are ignored.

    A valid response returns a result whose ``data`` is the parsed object.
    Any problem returns ``data`` as ``None`` and one or more errors.
    Malformed JSON and a non-object value produce a single error. An
    object can produce several field errors, in schema order.

    Raises:
        ValueError: ``response`` is not a string, ``schema`` is not a
            dictionary, a schema key is not a string, or a schema value
            is not a type.
    """
    if not isinstance(response, str):
        raise ValueError(
            f"response must be a string, got {type(response).__name__}"
        )
    _validate_schema(schema)

    try:
        parsed = json.loads(response)
    except json.JSONDecodeError as exc:
        return _failure(
            f"Response is not valid JSON (line {exc.lineno}, column {exc.colno})."
        )

    if not isinstance(parsed, dict):
        return _failure(
            "Top-level JSON value must be an object, "
            f"got {type(parsed).__name__}."
        )

    errors = tuple(
        OutputError(message=error.message, field=error.key)
        for error in validate_config(parsed, schema)
    )
    if errors:
        return ValidationResult(errors=errors)
    return ValidationResult(errors=(), data=parsed)


def _failure(message: str) -> ValidationResult:
    return ValidationResult(errors=(OutputError(message=message),))


def _validate_schema(schema: object) -> None:
    """Reject a schema that cannot describe JSON fields."""
    if not isinstance(schema, dict):
        raise ValueError(
            f"schema must be a dictionary, got {type(schema).__name__}"
        )
    for key, expected in schema.items():
        if not isinstance(key, str):
            raise ValueError(
                f"schema keys must be strings, got {type(key).__name__}"
            )
        # list[str] and similar generics are not types. isinstance() would
        # raise TypeError later, so reject them here with a clear message.
        if not isinstance(expected, type):
            raise ValueError(
                "schema value for "
                f"{key!r} must be a type such as str or int, "
                f"got {type(expected).__name__}"
            )
