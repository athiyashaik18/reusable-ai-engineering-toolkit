"""Tests for the configuration validator.

The cases use small fictional settings. They do not read files,
credentials, or external services.
"""

from typing import Any

import pytest

from config_validator import validate_config


SETTINGS_SCHEMA: dict[str, type[Any]] = {
    "app_name": str,
    "max_retries": int,
    "debug": bool,
}


def test_valid_configuration() -> None:
    errors = validate_config(
        {"app_name": "notebook-helper", "max_retries": 3, "debug": False},
        SETTINGS_SCHEMA,
    )

    assert errors == []


def test_missing_keys() -> None:
    errors = validate_config({"app_name": "notebook-helper"}, SETTINGS_SCHEMA)

    assert [error.key for error in errors] == ["max_retries", "debug"]
    assert errors[0].message == "max_retries is missing. Add it with a value of type int."
    assert errors[1].message == "debug is missing. Add it with a value of type bool."


def test_incorrect_type() -> None:
    errors = validate_config(
        {"app_name": 12, "max_retries": 3, "debug": False},
        SETTINGS_SCHEMA,
    )

    assert [error.key for error in errors] == ["app_name"]
    assert errors[0].message == "app_name must be a str, got int."


def test_multiple_errors_in_schema_order() -> None:
    errors = validate_config(
        {"app_name": 5, "debug": "yes"},
        SETTINGS_SCHEMA,
    )

    assert [error.key for error in errors] == ["app_name", "max_retries", "debug"]
    assert "must be a str" in errors[0].message
    assert "is missing" in errors[1].message
    assert "must be a bool" in errors[2].message


def test_empty_configuration_and_schema() -> None:
    assert validate_config({}, {}) == []


def test_configuration_with_no_required_keys() -> None:
    errors = validate_config(
        {"app_name": "notebook-helper", "max_retries": True},
        {},
    )

    assert errors == []


def test_empty_configuration_reports_every_missing_key() -> None:
    errors = validate_config({}, SETTINGS_SCHEMA)

    assert [error.key for error in errors] == ["app_name", "max_retries", "debug"]
    assert all("is missing" in error.message for error in errors)


def test_boolean_is_not_accepted_as_an_integer() -> None:
    for value in (True, False):
        errors = validate_config(
            {"app_name": "notebook-helper", "max_retries": value, "debug": True},
            SETTINGS_SCHEMA,
        )

        assert [error.key for error in errors] == ["max_retries"]
        assert errors[0].message == (
            "max_retries must be an int, got bool. "
            "Booleans are not integers."
        )


def test_wrong_type_message_omits_the_configuration_value() -> None:
    secret = "sk-live-DO-NOT-LEAK-notebook-token"
    errors = validate_config(
        {"app_name": "notebook-helper", "max_retries": secret, "debug": False},
        SETTINGS_SCHEMA,
    )

    assert [error.key for error in errors] == ["max_retries"]
    assert errors[0].message == "max_retries must be an int, got str."
    assert secret not in errors[0].message


def test_integer_is_not_accepted_as_a_boolean() -> None:
    errors = validate_config(
        {"app_name": "notebook-helper", "max_retries": 1, "debug": 1},
        SETTINGS_SCHEMA,
    )

    assert [error.key for error in errors] == ["debug"]
    assert errors[0].message == "debug must be a bool, got int."


def test_zero_and_false_are_present_values() -> None:
    errors = validate_config(
        {"app_name": "notebook-helper", "max_retries": 0, "debug": False},
        SETTINGS_SCHEMA,
    )

    assert errors == []


def test_ignores_keys_that_are_not_in_the_schema() -> None:
    errors = validate_config(
        {
            "app_name": "notebook-helper",
            "max_retries": 2,
            "debug": True,
            "notes": "not part of the schema",
        },
        SETTINGS_SCHEMA,
    )

    assert errors == []


def test_invalid_arguments_raise_value_error() -> None:
    bad_config: Any = ["notebook-helper"]
    bad_schema: Any = ["app_name"]
    schema_with_text: Any = {"app_name": "str"}

    with pytest.raises(ValueError, match="config must be a dictionary"):
        validate_config(bad_config, SETTINGS_SCHEMA)
    with pytest.raises(ValueError, match="schema must be a dictionary"):
        validate_config({}, bad_schema)
    with pytest.raises(ValueError, match="must be a type"):
        validate_config({}, schema_with_text)
