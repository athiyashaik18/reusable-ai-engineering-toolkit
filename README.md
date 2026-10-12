# reusable-ai-engineering-toolkit

A small Python toolkit for day-to-day work with RAG pipelines, LLM calls, and automation agents. Each utility is meant to be short, typed, and covered by tests so it can be reused across personal projects and shown in a portfolio.

This repository is being built one piece at a time. It currently contains a retry helper, a configuration validator, a character-based text chunker, a structured logger, and an LLM output validator.

## Purpose

Network calls and model APIs fail for reasons that are often temporary: a timeout, a rate limit, or a brief service error. Repeating that same retry loop in every script makes the code harder to read and easier to get wrong. This toolkit keeps that shared logic in one place.

`retry_utils.py` holds the retry helper. `config_validator.py` checks that a settings dictionary has its required keys and that each value has the expected type. `text_chunker.py` splits a document into character windows with a fixed size and overlap. `structured_logger.py` creates a named logger that can attach a few context fields to each event. `llm_output_validator.py` checks that a model's JSON text is an object with the required fields and types. Later modules can follow the same layout: one focused module, tests beside it, and a short example.

## Planned features

1. **Retry helper** (implemented). Retry a function when a chosen exception is raised, up to a fixed number of attempts, waiting with exponential backoff between attempts. Jitter is not included yet.
2. **Configuration validator** (implemented). Check a dictionary against a schema of required keys and expected types, and return every problem that was found.
3. **Text chunker** (implemented). Split a string into character windows using a maximum size and an overlap. Token-based splitting is not included yet.
4. **Structured logger** (implemented). Create a named logger at a chosen level and attach simple context fields. Secret-looking field names and whole configuration objects are rejected.
5. **LLM output validator** (implemented). Parse a JSON string and check required fields and types. Error messages do not include the raw response or field values.
6. **Further utilities**, added after the current helpers have been reviewed. Likely later topics include small helpers for RAG and agent workflows. Each one will get its own module, tests, and example.

## Project layout

```text
reusable-ai-engineering-toolkit/
├── retry_utils.py              # Retry helper
├── config_validator.py         # Configuration validator
├── text_chunker.py             # Character-based text chunker
├── structured_logger.py        # Named logger with context fields
├── llm_output_validator.py     # JSON output checks for model replies
├── tests/
│   ├── test_retry_utils.py     # Pytest suite for the retry helper
│   ├── test_config_validator.py
│   ├── test_text_chunker.py
│   ├── test_structured_logger.py
│   └── test_llm_output_validator.py
├── examples/
│   ├── retry_example.py        # Simulated transient failure
│   ├── config_example.py       # Fictional application settings
│   ├── chunk_example.py        # Fictional document note
│   ├── log_example.py          # Fictional retrieval events
│   └── llm_output_example.py   # Fictional model replies
├── README.md
└── .gitignore
```

## Prerequisites

- Python 3.11 or newer.
- [pytest](https://docs.pytest.org/) to run the tests.

The helpers use only the Python standard library. pytest is used by the test files and is not imported by the helpers.

From the `reusable-ai-engineering-toolkit` directory, a typical local setup is:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install pytest
```

macOS or Linux:

```bash
source .venv/bin/activate
python -m pip install pytest
```

## Retry helper

```python
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
```

`P` and `R` are typing variables. `R` is the wrapped function's return type, so a successful call is typed as whatever `func` returns.

| Argument | Required | Default | Meaning |
| --- | --- | --- | --- |
| `func` | yes | — | Callable to run. It is positional-only. |
| `*args`, `**kwargs` | no | — | Forwarded to `func` on every attempt. |
| `retry_on` | yes | — | Tuple of exception types that may be retried. Subclasses of those types are retried too. |
| `max_attempts` | no | `3` | Total attempts, including the first call. Must be an integer greater than or equal to 1. |
| `initial_delay` | no | `0.5` | Seconds to wait after the first retryable failure. `0` is allowed. Must be a finite number greater than or equal to 0. |
| `backoff_factor` | no | `2.0` | Multiplier applied after each wait. Must be a finite number greater than or equal to 1. |

### Behavior

1. The helper checks the settings and raises `ValueError` before calling `func` when a setting is invalid.
2. It calls `func(*args, **kwargs)`.
3. If `func` returns, that value is returned immediately.
4. If `func` raises a type listed in `retry_on`, and attempts remain, it sleeps, then tries again.
5. The first wait is `initial_delay`. Each following wait is the previous wait multiplied by `backoff_factor`. Default waits for three attempts are `0.5` seconds and then `1.0` seconds. There is no sleep after the last attempt.
6. If the last attempt raises a retryable exception, that same exception is raised again. It is not wrapped in a new error.
7. If `func` raises any other exception, including `KeyboardInterrupt` and `SystemExit`, it propagates immediately and is not retried.

`retry_on` has no default. Retrying every `Exception` would also retry programming errors such as `TypeError`. Pass the failures you know are temporary, for example `(TimeoutError, ConnectionError)`.

An empty tuple is valid. It means nothing is retried.

### Usage

```python
from retry_utils import retry

def load_document() -> str:
    ...

document = retry(
    load_document,
    retry_on=(TimeoutError, ConnectionError),
    max_attempts=4,
    initial_delay=0.5,
    backoff_factor=2.0,
)
```

Settings are keyword-only. They share the keyword namespace with `func`. If `func` already has an argument named `retry_on`, `max_attempts`, `initial_delay`, or `backoff_factor`, wrap the call:

```python
retry(lambda: func(retry_on=True), retry_on=(TimeoutError,))
```

A runnable simulation lives in `examples/retry_example.py`. From `reusable-ai-engineering-toolkit`:

```bash
python examples/retry_example.py
```

The example fails twice with `ConnectionError`, then returns `"retrieved document"`. It does not contact an external service.

### Limitations

- The wait uses `time.sleep`, so the helper blocks the current thread. There is no async version.
- Waits are exact exponential backoff. There is no jitter.
- Only raised exceptions can trigger a retry. A bad return value, such as an HTTP 429 inside a response object, is not inspected.
- `retry_on` accepts subclasses of `Exception` only. `BaseException`, `KeyboardInterrupt`, and `SystemExit` are rejected so cancellation is not swallowed.
- `backoff_factor` must be at least 1. A smaller factor would shorten the wait instead of backing off.
- This is a general helper. Client libraries that already retry, or that need retry based on status codes, should keep that logic in the caller.

## Configuration validator

```python
def validate_config(
    config: dict[str, Any],
    schema: dict[str, type[Any]],
) -> list[ConfigError]:
```

`schema` maps each required key to one type, such as `str`, `int`, `float`, or `bool`. The function returns a list of `ConfigError` values. Each error has the key that failed and a message that says what to change. An empty list means the dictionary matches the schema.

| Argument | Meaning |
| --- | --- |
| `config` | Settings to check. An empty dictionary is valid when the schema has no required keys. |
| `schema` | Required keys and the type of each value. An empty schema requires nothing. |

### Behavior

1. Arguments that are not dictionaries, schema keys that are not strings, and schema values that are not real types raise `ValueError` before any field is checked.
2. Every schema key must be present in `config`. A missing key produces an error that names the key and the type to add.
3. A present value must be an instance of the expected type. `True` and `False` are not accepted where an `int` is required, because `bool` is a subclass of `int`.
4. `0` and `False` are real values. They are not treated as missing.
5. All problems are returned together, in schema key order. The function does not stop at the first error.
6. Keys that are not listed in the schema are ignored.

### Usage

```python
from config_validator import validate_config

schema = {
    "app_name": str,
    "max_retries": int,
    "debug": bool,
}
errors = validate_config(
    {"app_name": "notebook-helper", "max_retries": 3, "debug": False},
    schema,
)
if errors:
    raise ValueError("\n".join(error.message for error in errors))
```

A runnable demonstration lives in `examples/config_example.py`. From `reusable-ai-engineering-toolkit`:

```bash
python examples/config_example.py
```

The example checks made-up settings for an application named `notebook-helper`. It does not read credentials or contact an external service.

### Limitations

- Every key in the schema is required. Optional keys are not represented yet.
- Each key has one concrete type. The schema does not accept unions, `list[str]`, numeric ranges, or string formats.
- Nested dictionaries are not validated field by field. A nested dictionary can only be required to be a `dict`.
- Unknown keys are ignored, so a typo in a key name is reported as a missing required key only when the correctly spelled key is absent.
- Subclasses of the expected type are accepted, except that `bool` is not accepted as `int`.

## Text chunker

```python
def chunk_text(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
```

`chunk_text` splits a document into windows of at most `chunk_size` characters. `overlap` is how many characters the next window repeats from the previous one. The default overlap is `0`.

| Argument | Required | Default | Meaning |
| --- | --- | --- | --- |
| `text` | yes | — | Document to split. An empty string produces no chunks. |
| `chunk_size` | yes | — | Maximum characters in a chunk. Must be an integer greater than or equal to 1. |
| `overlap` | no | `0` | Characters repeated at the start of the next chunk. Must be an integer such that `0 <= overlap < chunk_size`. |

### Behavior

1. Invalid `text`, `chunk_size`, or `overlap` raises `ValueError` before any slice is taken. `True` and `False` are not accepted as integers.
2. An empty string returns `[]`.
3. Text shorter than `chunk_size`, or exactly `chunk_size`, returns one chunk equal to the original string.
4. Longer text is sliced into windows. The next window starts `chunk_size - overlap` characters after the previous start.
5. The window that first reaches the end of the text is the last chunk. The final window may be shorter than `chunk_size`.
6. Each chunk is an exact slice. Spaces, newlines, and punctuation stay as they were. Characters are not stripped.
7. Because overlap is smaller than the chunk size, the start index increases by at least one character every time. The loop cannot stay on the same window.

With `chunk_size=4` and `overlap=1`, `"abcdefghij"` becomes `["abcd", "defg", "ghij"]`.

### Usage

```python
from text_chunker import chunk_text

chunks = chunk_text(
    "Monday note: Ada asked how to split long notes.",
    chunk_size=24,
    overlap=5,
)
```

When `overlap` is `0`, `"".join(chunks)` is the original text. When `overlap` is greater than `0`, shared characters appear in two neighboring chunks, so joining the chunks repeats those characters.

A runnable note lives in `examples/chunk_example.py`. From `reusable-ai-engineering-toolkit`:

```bash
python examples/chunk_example.py
```

The example splits a fictional study-group note. It does not read a file or contact an external service.

### Limitations

- Windows are counted in Python characters, the same way `len()` counts them. This is not a token or word splitter.
- A window can start or end in the middle of a word. Sentence and paragraph boundaries are not detected.
- Overlap copies characters into the next chunk. Joining the chunks rebuilds the document only when `overlap` is `0`.
- The chunker does not drop or rewrite whitespace. It also does not add separators between chunks.

## Structured logger

```python
def get_logger(name: str, level: int | str = logging.INFO) -> StructuredLogger:
```

`get_logger` returns a `StructuredLogger` for `name`. The first call installs one handler. A later call with the same name changes the level and keeps that handler, so messages are not written twice by duplicate handlers.

`level` may be `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. Names are not case-sensitive. The same values from the `logging` module, such as `logging.INFO`, are also accepted. The default is `INFO`.

| Method | When to use it |
| --- | --- |
| `debug` | Detail you want only while diagnosing a problem. |
| `info` | A normal step, such as a finished retrieval. |
| `warning` | Something unexpected that did not stop the operation. |
| `error` | An operation failed. |
| `critical` | A failure that needs immediate attention. |

Each method takes a message and optional keyword fields. A field value must be a `str`, `int`, `float`, `bool`, or `None`.

### Behavior

1. An empty name, a non-string name, or an unknown level raises `ValueError` before a handler is added.
2. The logger writes lines to the standard error stream in the form `LEVEL name message field=value`.
3. Fields are appended in the order they were passed. `True` and `False` are written as `true` and `false`.
4. Records are not forwarded to parent loggers. `propagate` is `False`, so a root handler does not print the same line again.
5. Field names such as `password`, `token`, `api_key`, and `secret` are rejected. The rejected value is not included in the error.
6. Dictionaries, lists, and other objects are rejected, so a whole configuration object is not written to the log.
7. Events below the configured level are discarded. A logger set to `WARNING` does not emit an `info` event.

### Usage

```python
from structured_logger import get_logger

logger = get_logger("notebook-helper", level="INFO")
logger.info(
    "retrieval finished",
    operation="search",
    request_id="req-1001",
    status="ok",
    duration_ms=18,
)
```

That call writes a line like:

```text
INFO notebook-helper retrieval finished operation=search request_id=req-1001 status=ok duration_ms=18
```

A runnable script lives in `examples/log_example.py`. From `reusable-ai-engineering-toolkit`:

```bash
python examples/log_example.py
```

The example logs a fictional search. It does not read credentials or contact an external service.

### Limitations

- Fields are plain text on the log line. The logger does not emit JSON.
- The factory's handler writes to standard error. It does not rotate files or ship logs to another service.
- `propagate` is turned off for loggers created here. Parent or root handlers do not receive these records.
- Only the listed field names are blocked. A secret placed in a field named `status` is still logged. This is not a general secret scanner.
- Calling `get_logger` again updates the level of the existing logger. It does not create a second independent logger with the same name.

## LLM output validator

```python
def validate_llm_output(
    response: str,
    schema: dict[str, type[Any]],
) -> ValidationResult:
```

`validate_llm_output` parses `response` with `json.loads` and checks it against `schema`. The schema maps each required field name to one Python type. Field checks use the same rules as the configuration validator.

The result has three useful parts:

| Part | Meaning |
| --- | --- |
| `is_valid` | `True` when there are no errors. |
| `errors` | Zero or more `OutputError` values. Each has a `message` and, for a field problem, a `field` name. |
| `data` | The parsed object when the response is valid. `None` when it is not. |

### Behavior

1. A response that is not a string, or a schema that is not a dictionary of types, raises `ValueError`. Those errors do not include the response text.
2. Malformed JSON returns one error with the line and column. The raw text is not copied into the message.
3. The top-level JSON value must be an object. An array, string, number, Boolean, or `null` returns one error naming the Python type that was found.
4. Each schema key must be present. A missing key produces an error that names the field and the type to add.
5. A present value must be an instance of the expected type. `true` and `false` are not accepted where an `int` is required. `null` is a type error, not a missing field.
6. All field problems in one object are returned together, in schema key order.
7. Messages name the field and the expected and actual types. They do not include the raw response or the field value.
8. Fields that are not listed in the schema are not checked. When the response is valid, those fields remain in `data`.

### Usage

```python
from llm_output_validator import validate_llm_output

schema = {"answer": str, "score": int, "confident": bool}
result = validate_llm_output(
    '{"answer": "The study group met on Monday.", "score": 3, "confident": false}',
    schema,
)
if not result.is_valid:
    raise ValueError(str(result))
answer = result.data["answer"]
```

A runnable pair of fictional replies lives in `examples/llm_output_example.py`. From `reusable-ai-engineering-toolkit`:

```bash
python examples/llm_output_example.py
```

The example does not call a model or contact an external service.

### Limitations

- The text must be JSON by itself. A markdown fence or a sentence before the object is malformed JSON.
- Every schema key is required. Optional fields are not represented yet.
- Each field has one concrete type. Nested objects can be required to be a `dict`, but their inner fields are not checked. List items are not checked either.
- A JSON number with no decimal point is an `int`. It is not accepted for a `float` field.
- Extra fields are ignored. A typo in a field name is reported only as a missing required field.
- `data` holds the parsed object after a successful check, so callers that print `data` will show those values. Error messages do not.

## How to run tests

From `reusable-ai-engineering-toolkit`:

```bash
python -m pytest
```

To run only the retry tests:

```bash
python -m pytest tests/test_retry_utils.py
```

To run only the configuration tests:

```bash
python -m pytest tests/test_config_validator.py
```

To run only the chunker tests:

```bash
python -m pytest tests/test_text_chunker.py
```

To run only the logger tests:

```bash
python -m pytest tests/test_structured_logger.py
```

To run only the LLM output tests:

```bash
python -m pytest tests/test_llm_output_validator.py
```

The retry tests replace `time.sleep` with a recorder. They do not wait on the real clock and they do not make network calls. The configuration tests use plain dictionaries, the chunker tests use plain strings, the logger tests use the standard-library logging module, and the LLM output tests use local JSON strings. None of them read files, call a model, or use the network.

## Current status

| Item | Status |
| --- | --- |
| Project folders | Created |
| Retry helper | Implemented in `retry_utils.py` |
| Retry tests | Implemented in `tests/test_retry_utils.py` |
| Retry example | Simulated failure in `examples/retry_example.py` |
| Configuration validator | Implemented in `config_validator.py` |
| Configuration tests | Implemented in `tests/test_config_validator.py` |
| Configuration example | Fictional settings in `examples/config_example.py` |
| Text chunker | Implemented in `text_chunker.py` |
| Chunker tests | Implemented in `tests/test_text_chunker.py` |
| Chunker example | Fictional note in `examples/chunk_example.py` |
| Structured logger | Implemented in `structured_logger.py` |
| Logger tests | Implemented in `tests/test_structured_logger.py` |
| Logger example | Fictional events in `examples/log_example.py` |
| LLM output validator | Implemented in `llm_output_validator.py` |
| LLM output tests | Implemented in `tests/test_llm_output_validator.py` |
| LLM output example | Fictional replies in `examples/llm_output_example.py` |
| Jitter, async retry, optional keys, token-based chunking, JSON logging, nested JSON schemas, and later toolkit modules | Not started |
