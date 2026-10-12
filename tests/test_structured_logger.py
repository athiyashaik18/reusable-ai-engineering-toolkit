"""Tests for the structured logger.

Loggers use unique names so one test does not change another's handler.
The samples are fictional and contain no credentials.
"""

import logging

import pytest

from structured_logger import get_logger


class _Capture(logging.Handler):
    """Store formatted messages from one test logger."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _attach_capture(name: str) -> _Capture:
    capture = _Capture()
    logging.getLogger(name).addHandler(capture)
    return capture


def test_creates_a_named_logger() -> None:
    logger = get_logger("reusable_toolkit.tests.creation")

    assert logger.name == "reusable_toolkit.tests.creation"
    assert logger.level == logging.INFO
    raw = logging.getLogger(logger.name)
    assert raw.propagate is False
    assert len(raw.handlers) == 1


def test_accepts_level_names_and_constants() -> None:
    by_name = get_logger("reusable_toolkit.tests.level-name", level="warning")
    by_constant = get_logger("reusable_toolkit.tests.level-constant", level=logging.DEBUG)

    assert by_name.level == logging.WARNING
    assert by_constant.level == logging.DEBUG


def test_configured_level_filters_lower_events() -> None:
    name = "reusable_toolkit.tests.levels"
    logger = get_logger(name, level="WARNING")
    capture = _attach_capture(name)

    logger.info("retrieval finished", operation="search")
    logger.warning("retrieval was slow", status="slow")

    assert capture.messages == ["retrieval was slow status=slow"]


def test_structured_fields_keep_call_order() -> None:
    name = "reusable_toolkit.tests.fields"
    logger = get_logger(name, level="INFO")
    capture = _attach_capture(name)

    logger.info(
        "retrieval finished",
        operation="search",
        request_id="req-1001",
        status="ok",
        duration_ms=18,
    )

    assert capture.messages == [
        "retrieval finished operation=search request_id=req-1001 status=ok duration_ms=18"
    ]


def test_repeated_factory_calls_do_not_add_handlers() -> None:
    name = "reusable_toolkit.tests.repeated"
    raw = logging.getLogger(name)
    raw.handlers.clear()

    get_logger(name, level="INFO")
    assert len(raw.handlers) == 1

    get_logger(name, level="DEBUG")
    assert len(raw.handlers) == 1
    assert raw.level == logging.DEBUG

    capture = _attach_capture(name)
    get_logger(name, level="DEBUG").info("retrieval finished", operation="search")
    assert capture.messages == ["retrieval finished operation=search"]


@pytest.mark.parametrize(
    ("name", "level", "message"),
    [
        ("", "INFO", "logger name"),
        ("   ", "INFO", "logger name"),
        (None, "INFO", "logger name"),
        ("reusable_toolkit.tests.invalid", "VERBOSE", "level must be"),
        ("reusable_toolkit.tests.invalid", True, "level must be"),
        ("reusable_toolkit.tests.invalid", 15, "level must be"),
    ],
)
def test_invalid_logger_configuration(
    name: object,
    level: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        get_logger(name, level)  # type: ignore[arg-type]


def test_secret_field_is_rejected_without_the_value() -> None:
    logger = get_logger("reusable_toolkit.tests.secrets", level="INFO")
    secret = "sk-live-DO-NOT-LEAK-token"

    with pytest.raises(ValueError, match="not logged") as caught:
        logger.info("call failed", api_key=secret)

    assert secret not in str(caught.value)


def test_configuration_object_is_rejected_without_its_contents() -> None:
    logger = get_logger("reusable_toolkit.tests.config-object", level="INFO")
    secret = "sk-live-DO-NOT-LEAK-config"

    with pytest.raises(ValueError, match="Configuration objects are not logged") as caught:
        logger.info("startup", settings={"api_key": secret, "model": "demo"})

    assert secret not in str(caught.value)


def test_unrecognized_level_does_not_echo_the_value() -> None:
    secret = "sk-live-DO-NOT-LEAK-level"

    with pytest.raises(ValueError, match="level must be") as caught:
        get_logger("reusable_toolkit.tests.secret-level", level=secret)

    assert secret not in str(caught.value)
