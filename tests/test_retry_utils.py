"""Tests for the retry helper.

Sleep is replaced with a recorder so the tests stay fast and do not
depend on the clock. No network or external service is used.
"""

import pytest

from retry_utils import retry


def _record_sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Replace time.sleep with a function that stores the requested delays."""
    recorded: list[float] = []

    def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr("retry_utils.time.sleep", fake_sleep)
    return recorded


def test_success_on_first_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _record_sleeps(monkeypatch)

    def succeed() -> str:
        return "ready"

    assert retry(succeed, retry_on=(TimeoutError,)) == "ready"
    assert sleeps == []


def test_success_after_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _record_sleeps(monkeypatch)
    calls = {"count": 0}

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("temporary timeout")
        return "ok"

    result = retry(flaky, retry_on=(TimeoutError,), initial_delay=0.5, backoff_factor=2.0)

    assert result == "ok"
    assert calls["count"] == 2
    assert sleeps == [0.5]


def test_failure_after_all_attempts_are_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _record_sleeps(monkeypatch)

    def always_fail() -> None:
        raise ConnectionError("down")

    with pytest.raises(ConnectionError, match="down"):
        retry(
            always_fail,
            retry_on=(ConnectionError,),
            max_attempts=3,
            initial_delay=0.5,
            backoff_factor=2.0,
        )

    assert sleeps == [0.5, 1.0]


def test_does_not_retry_unlisted_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _record_sleeps(monkeypatch)
    calls = {"count": 0}

    def boom() -> None:
        calls["count"] += 1
        raise ValueError("bad input")

    with pytest.raises(ValueError, match="bad input"):
        retry(boom, retry_on=(TimeoutError, ConnectionError), max_attempts=5)

    assert calls["count"] == 1
    assert sleeps == []


def test_retries_subclass_of_configured_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _record_sleeps(monkeypatch)
    calls = {"count": 0}

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] == 1:
            raise ConnectionResetError("reset")
        return "recovered"

    result = retry(flaky, retry_on=(ConnectionError,), initial_delay=0)

    assert result == "recovered"
    assert calls["count"] == 2
    assert sleeps == [0.0]


def test_single_attempt_does_not_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _record_sleeps(monkeypatch)

    def always_fail() -> None:
        raise TimeoutError("down")

    with pytest.raises(TimeoutError):
        retry(always_fail, retry_on=(TimeoutError,), max_attempts=1, initial_delay=0.5)

    assert sleeps == []


def test_stops_on_unlisted_exception_after_a_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _record_sleeps(monkeypatch)
    calls = {"count": 0}

    def flaky() -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("temporary")
        raise ValueError("not retryable")

    with pytest.raises(ValueError, match="not retryable"):
        retry(flaky, retry_on=(TimeoutError,), max_attempts=4, initial_delay=0)

    assert calls["count"] == 2
    assert sleeps == [0.0]


def test_uses_the_requested_number_of_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    _record_sleeps(monkeypatch)
    calls = {"count": 0}

    def always_fail() -> None:
        calls["count"] += 1
        raise ConnectionError("down")

    with pytest.raises(ConnectionError):
        retry(always_fail, retry_on=(ConnectionError,), max_attempts=5, initial_delay=0)

    assert calls["count"] == 5


def test_exponential_backoff_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _record_sleeps(monkeypatch)

    def always_fail() -> None:
        raise TimeoutError("still down")

    with pytest.raises(TimeoutError):
        retry(
            always_fail,
            retry_on=(TimeoutError,),
            max_attempts=4,
            initial_delay=0.5,
            backoff_factor=2.0,
        )

    assert sleeps == [0.5, 1.0, 2.0]


def test_zero_delay_does_not_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _record_sleeps(monkeypatch)

    def always_fail() -> None:
        raise TimeoutError("down")

    with pytest.raises(TimeoutError):
        retry(
            always_fail,
            retry_on=(TimeoutError,),
            max_attempts=3,
            initial_delay=0,
            backoff_factor=2.0,
        )

    assert sleeps == [0.0, 0.0]


def test_passes_arguments_through_to_the_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    _record_sleeps(monkeypatch)

    def add(left: int, right: int, *, scale: int = 1) -> int:
        return (left + right) * scale

    assert retry(add, 2, 3, retry_on=(TimeoutError,), scale=4) == 20


def test_reraises_the_final_exception_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    _record_sleeps(monkeypatch)
    raised: list[ConnectionError] = []

    def always_fail() -> None:
        error = ConnectionError(f"attempt {len(raised) + 1}")
        raised.append(error)
        raise error

    with pytest.raises(ConnectionError) as caught:
        retry(always_fail, retry_on=(ConnectionError,), max_attempts=3, initial_delay=0)

    assert caught.value is raised[-1]
    assert str(caught.value) == "attempt 3"


def test_keyboard_interrupt_is_not_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps = _record_sleeps(monkeypatch)
    calls = {"count": 0}

    def cancelled() -> None:
        calls["count"] += 1
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        retry(cancelled, retry_on=(Exception,), max_attempts=3)

    assert calls["count"] == 1
    assert sleeps == []


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"max_attempts": 0}, "max_attempts"),
        ({"max_attempts": -3}, "max_attempts"),
        ({"max_attempts": True}, "max_attempts"),
        ({"max_attempts": 1.5}, "max_attempts"),
        ({"initial_delay": -0.1}, "initial_delay"),
        ({"initial_delay": float("nan")}, "initial_delay"),
        ({"initial_delay": float("inf")}, "initial_delay"),
        ({"initial_delay": True}, "initial_delay"),
        ({"backoff_factor": 0.5}, "backoff_factor"),
        ({"backoff_factor": 0}, "backoff_factor"),
        ({"backoff_factor": -1}, "backoff_factor"),
        ({"backoff_factor": float("nan")}, "backoff_factor"),
        ({"retry_on": TimeoutError}, "retry_on"),
        ({"retry_on": (KeyboardInterrupt,)}, "retry_on"),
        ({"retry_on": (BaseException,)}, "retry_on"),
        ({"retry_on": (TimeoutError, "ConnectionError")}, "retry_on"),
    ],
)
def test_invalid_configuration_raises_value_error(
    overrides: dict[str, object],
    message: str,
) -> None:
    settings: dict[str, object] = {"retry_on": (TimeoutError,)}
    settings.update(overrides)

    def should_not_run() -> str:
        raise AssertionError("callable should not run when configuration is invalid")

    # The invalid values are intentional, so the type checker is told to allow them.
    with pytest.raises(ValueError, match=message):
        retry(should_not_run, **settings)  # type: ignore[arg-type]
