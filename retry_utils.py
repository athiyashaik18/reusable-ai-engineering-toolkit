"""Reusable retry helpers for calls that can fail temporarily.

Typical callers are LLM requests, retrieval steps in a RAG pipeline, and
steps inside an automation agent. The helper knows how to wait and try
again. The caller decides which failures are temporary.
"""

import math
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

# P tracks the wrapped function's parameters. R tracks its return type,
# so a successful retry(...) call is typed as whatever func returns.
P = ParamSpec("P")
R = TypeVar("R")


def retry(
    func: Callable[P, R],
    /,
    *args: P.args,
    retry_on: tuple[type[Exception], ...],
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    **kwargs: P.kwargs,
) -> R:
    """Call ``func`` until it returns or the attempt limit is reached.

    Positional and keyword arguments other than the settings below are
    forwarded to ``func``. Pass every setting by keyword.

    After a retryable failure, this sleeps for ``initial_delay`` seconds.
    Each later wait is the previous wait multiplied by ``backoff_factor``.
    With the defaults, the waits are 0.5 seconds and then 1.0 seconds.
    There is no sleep after the final attempt.

    ``retry_on`` is required. Only those exception types, including their
    subclasses, are retried. ``KeyboardInterrupt`` and ``SystemExit`` are
    not subclasses of ``Exception``, so they are never caught here.

    Raises:
        ValueError: One of the settings is invalid.
        Exception: The final attempt raised a type listed in ``retry_on``.
            Any other exception raised by ``func`` propagates immediately.
    """
    _validate_config(retry_on, max_attempts, initial_delay, backoff_factor)

    delay = float(initial_delay)
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except retry_on:
            is_last_attempt = attempt == max_attempts - 1
            if is_last_attempt:
                raise
            time.sleep(delay)
            delay *= backoff_factor

    # max_attempts is at least 1, so the loop always returns or raises.
    raise RuntimeError("retry ended without a result or an exception")


def _validate_config(
    retry_on: tuple[type[Exception], ...],
    max_attempts: int,
    initial_delay: float,
    backoff_factor: float,
) -> None:
    """Reject settings that would make the retry loop unsafe or unclear."""
    if not isinstance(retry_on, tuple):
        raise ValueError(
            "retry_on must be a tuple of exception types, "
            f"got {type(retry_on).__name__}"
        )
    for exc_type in retry_on:
        # BaseException, KeyboardInterrupt, and SystemExit fail this check.
        # Catching them would swallow cancellation and interpreter shutdown.
        if not isinstance(exc_type, type) or not issubclass(exc_type, Exception):
            raise ValueError(
                "retry_on must contain only subclasses of Exception. "
                "BaseException and its non-Exception subclasses, such as "
                f"KeyboardInterrupt, cannot be retried. Got {exc_type!r}."
            )

    # bool is a subclass of int, so True would otherwise pass an int check.
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
        raise ValueError(
            "max_attempts must be an integer greater than or equal to 1, "
            f"got {max_attempts!r}"
        )
    if max_attempts < 1:
        raise ValueError(
            "max_attempts must be greater than or equal to 1, "
            f"got {max_attempts!r}"
        )

    # Check the type first. math.isfinite() raises TypeError for non-numbers.
    delay_is_valid = (
        _is_real_number(initial_delay)
        and math.isfinite(initial_delay)
        and initial_delay >= 0
    )
    if not delay_is_valid:
        raise ValueError(
            "initial_delay must be a finite number greater than or equal to 0, "
            f"got {initial_delay!r}"
        )

    # A factor below 1 would shrink the wait, which is not backoff.
    factor_is_valid = (
        _is_real_number(backoff_factor)
        and math.isfinite(backoff_factor)
        and backoff_factor >= 1
    )
    if not factor_is_valid:
        raise ValueError(
            "backoff_factor must be a finite number greater than or equal to 1, "
            f"got {backoff_factor!r}"
        )


def _is_real_number(value: object) -> bool:
    """Return True for int and float, and False for bool and other types."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)
