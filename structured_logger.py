"""Named loggers that attach a few context fields to each event.

The factory uses the standard-library logging module. A second call for
the same name updates the level and does not add another handler.
"""

import logging
import threading

_STANDARD_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
_LEVEL_BY_VALUE = {value: name for name, value in _STANDARD_LEVELS.items()}

# Exact field names that should not be written to a log line. The check
# does not inspect the characters inside an ordinary string value.
_SECRET_FIELD_NAMES = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "credential",
        "credentials",
        "authorization",
        "access_key",
        "secret_key",
    }
)
_HANDLER_NAME = "reusable-ai-toolkit"
_setup_lock = threading.Lock()


class StructuredLogger:
    """Logger that writes a message plus simple context fields.

    Fields are text such as ``operation``, ``request_id``, ``status``, and
    ``duration_ms``. Pass those values directly. Do not pass a password,
    a token, or a whole configuration dictionary.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    @property
    def name(self) -> str:
        return self._logger.name

    @property
    def level(self) -> int:
        return self._logger.level

    def debug(self, message: str, **fields: object) -> None:
        """Log a debug event. ``fields`` are simple context values."""
        self._log(logging.DEBUG, message, fields)

    def info(self, message: str, **fields: object) -> None:
        """Log an info event. ``fields`` are simple context values."""
        self._log(logging.INFO, message, fields)

    def warning(self, message: str, **fields: object) -> None:
        """Log a warning event. ``fields`` are simple context values."""
        self._log(logging.WARNING, message, fields)

    def error(self, message: str, **fields: object) -> None:
        """Log an error event. ``fields`` are simple context values."""
        self._log(logging.ERROR, message, fields)

    def critical(self, message: str, **fields: object) -> None:
        """Log a critical event. ``fields`` are simple context values."""
        self._log(logging.CRITICAL, message, fields)

    def _log(self, level: int, message: str, fields: dict[str, object]) -> None:
        if not isinstance(message, str):
            raise ValueError(
                f"message must be a string, got {type(message).__name__}"
            )
        checked = _validate_fields(fields)
        text = message if not checked else f"{message} {_format_fields(checked)}"
        self._logger.log(level, text)


def get_logger(name: str, level: int | str = logging.INFO) -> StructuredLogger:
    """Return a named logger, adding its handler only on the first call.

    ``level`` is ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, or
    ``CRITICAL``, either as a name or as the matching ``logging`` constant.
    A later call with the same ``name`` applies the new level and keeps
    the existing handler.

    The logger writes to the standard error stream and does not forward
    records to parent loggers. Forwarding as well would print each line
    a second time when the root logger also has a handler.

    Raises:
        ValueError: ``name`` is empty or not a string, or ``level`` is
            not one of the five standard levels.
    """
    logger_name = _validate_name(name)
    resolved_level = _validate_level(level)
    logger = logging.getLogger(logger_name)
    # Two threads can pass the handler check together. The lock keeps
    # them from each adding a handler.
    with _setup_lock:
        logger.setLevel(resolved_level)
        logger.propagate = False
        if not any(handler.name == _HANDLER_NAME for handler in logger.handlers):
            handler = logging.StreamHandler()
            handler.name = _HANDLER_NAME
            handler.setFormatter(
                logging.Formatter("%(levelname)s %(name)s %(message)s")
            )
            logger.addHandler(handler)
    return StructuredLogger(logger)


def _validate_name(name: object) -> str:
    if not isinstance(name, str) or name.strip() == "":
        raise ValueError("logger name must be a non-empty string")
    return name


def _validate_level(level: object) -> int:
    if isinstance(level, str):
        resolved = _STANDARD_LEVELS.get(level.upper())
        if resolved is None:
            raise ValueError(
                "level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL"
            )
        return resolved
    # bool is a subclass of int, so reject it before the int check.
    if isinstance(level, bool) or not isinstance(level, int) or level not in _LEVEL_BY_VALUE:
        raise ValueError(
            "level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL"
        )
    return level


def _validate_fields(fields: dict[str, object]) -> dict[str, object]:
    checked: dict[str, object] = {}
    for name, value in fields.items():
        if not isinstance(name, str) or name.strip() == "":
            raise ValueError("field names must be non-empty strings")
        normalized = name.lower().replace("-", "_")
        if normalized in _SECRET_FIELD_NAMES:
            raise ValueError(
                f"field {name!r} is not logged because its name looks like a secret"
            )
        if not _is_simple_value(value):
            raise ValueError(
                f"field {name!r} must be a str, int, float, bool, or None, "
                f"got {type(value).__name__}. Configuration objects are not logged."
            )
        checked[name] = value
    return checked


def _is_simple_value(value: object) -> bool:
    if value is None or isinstance(value, (str, float, bool)):
        return True
    return isinstance(value, int) and not isinstance(value, bool)


def _format_fields(fields: dict[str, object]) -> str:
    return " ".join(
        f"{name}={_format_value(value)}" for name, value in fields.items()
    )


def _format_value(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        if value == "" or any(character.isspace() for character in value):
            return repr(value)
        return value
    return str(value)
