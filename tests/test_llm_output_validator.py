"""Tests for LLM JSON output validation.

The samples are fictional model replies. They do not call a model or
read credentials. Secret-looking strings are used only to prove that
error text leaves them out.
"""

import json
from typing import Any

import pytest

from llm_output_validator import validate_llm_output


ANSWER_SCHEMA: dict[str, type[Any]] = {
    "answer": str,
    "score": int,
    "confident": bool,
}


def test_valid_output() -> None:
    result = validate_llm_output(
        '{"answer": "The study group met on Monday.", "score": 3, "confident": false}',
        ANSWER_SCHEMA,
    )

    assert result.is_valid is True
    assert result.errors == ()
    assert result.data == {
        "answer": "The study group met on Monday.",
        "score": 3,
        "confident": False,
    }
    assert str(result) == "Validation succeeded."


def test_malformed_json() -> None:
    result = validate_llm_output("{", ANSWER_SCHEMA)

    assert result.is_valid is False
    assert result.data is None
    assert len(result.errors) == 1
    assert result.errors[0].field is None
    assert result.errors[0].message == "Response is not valid JSON (line 1, column 2)."


def test_missing_fields() -> None:
    result = validate_llm_output('{"answer": "Monday"}', ANSWER_SCHEMA)

    assert [error.field for error in result.errors] == ["score", "confident"]
    assert result.errors[0].message == "score is missing. Add it with a value of type int."
    assert result.errors[1].message == (
        "confident is missing. Add it with a value of type bool."
    )
    assert result.data is None


def test_incorrect_type() -> None:
    result = validate_llm_output(
        '{"answer": 12, "score": 3, "confident": false}',
        ANSWER_SCHEMA,
    )

    assert [error.field for error in result.errors] == ["answer"]
    assert result.errors[0].message == "answer must be a str, got int."


def test_null_is_a_type_error() -> None:
    result = validate_llm_output('{"answer": null}', {"answer": str})

    assert [error.field for error in result.errors] == ["answer"]
    assert result.errors[0].message == "answer must be a str, got NoneType."


def test_multiple_errors_in_schema_order() -> None:
    result = validate_llm_output(
        '{"answer": 5, "confident": "yes"}',
        ANSWER_SCHEMA,
    )

    assert [error.field for error in result.errors] == ["answer", "score", "confident"]
    assert "must be a str" in result.errors[0].message
    assert "is missing" in result.errors[1].message
    assert "must be a bool" in result.errors[2].message


@pytest.mark.parametrize(
    ("response", "actual_type"),
    [
        ("[]", "list"),
        ('"Monday"', "str"),
        ("3", "int"),
        ("1.5", "float"),
        ("true", "bool"),
        ("null", "NoneType"),
    ],
)
def test_non_object_json(response: str, actual_type: str) -> None:
    result = validate_llm_output(response, ANSWER_SCHEMA)

    assert result.is_valid is False
    assert result.data is None
    assert len(result.errors) == 1
    assert result.errors[0].field is None
    assert result.errors[0].message == (
        f"Top-level JSON value must be an object, got {actual_type}."
    )


def test_boolean_is_not_accepted_as_an_integer() -> None:
    for literal in ("true", "false"):
        result = validate_llm_output(
            f'{{"answer": "Monday", "score": {literal}, "confident": true}}',
            ANSWER_SCHEMA,
        )

        assert [error.field for error in result.errors] == ["score"]
        assert result.errors[0].message == (
            "score must be an int, got bool. Booleans are not integers."
        )
        assert literal not in result.errors[0].message


def test_integer_is_not_accepted_as_a_boolean() -> None:
    result = validate_llm_output(
        '{"answer": "Monday", "score": 1, "confident": 1}',
        ANSWER_SCHEMA,
    )

    assert [error.field for error in result.errors] == ["confident"]
    assert result.errors[0].message == "confident must be a bool, got int."


def test_empty_object_and_empty_schema() -> None:
    result = validate_llm_output("{}", {})

    assert result.is_valid is True
    assert result.data == {}


def test_unknown_fields_are_kept_but_not_required() -> None:
    result = validate_llm_output(
        '{"answer": "Monday", "score": 2, "confident": false, "note": "extra"}',
        ANSWER_SCHEMA,
    )

    assert result.is_valid is True
    assert result.data is not None
    assert result.data["note"] == "extra"


def test_error_messages_omit_the_response_and_field_values() -> None:
    secret = "sk-live-DO-NOT-LEAK-model-output"
    samples = [
        f'{{"answer": "{secret}"',
        json.dumps([secret]),
        json.dumps({"answer": secret, "score": secret, "confident": True}),
        json.dumps({"answer": secret}),
    ]

    for response in samples:
        result = validate_llm_output(response, ANSWER_SCHEMA)

        assert result.is_valid is False
        assert secret not in str(result)
        assert secret not in repr(result)
        assert all(secret not in error.message for error in result.errors)
        assert response not in str(result)
        assert response not in repr(result)


def test_invalid_arguments_do_not_echo_the_payload() -> None:
    secret = "sk-live-DO-NOT-LEAK-model-output"
    payload: Any = {"answer": secret}
    schema: Any = {"answer": "str"}

    with pytest.raises(ValueError, match="response must be a string") as bad_response:
        validate_llm_output(payload, ANSWER_SCHEMA)
    assert secret not in str(bad_response.value)

    with pytest.raises(ValueError, match="must be a type") as bad_schema:
        validate_llm_output(json.dumps({"answer": secret}), schema)
    assert secret not in str(bad_schema.value)
