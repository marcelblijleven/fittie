# Testing

Install the development environment with `uv sync --locked`, then run:

```shell
uv run pytest
uv run mypy fittie
uv run ruff check .
uv run ruff format --check .
```

Run one test file with `uv run pytest tests/fittie/fitfile/test_protocol.py`.
To apply formatting, use `uv run ruff format .`.
CI runs checks on Python 3.10, 3.11, 3.12, 3.13, and 3.14.

The protocol regression suite builds small FIT byte streams directly and does not
require a Garmin SDK download. The optional Garmin sample smoke tests discover
`.fit` files in `tests/data/from_garmin_sdk`; these files are ignored by Git, so a
fresh checkout skips that parameterized test. The CSV files are reference output,
not test inputs. See the [compatibility audit](fit-compatibility.md) for coverage
limits and the work needed for a reproducible Garmin comparison suite.

Build the documentation locally with:

```shell
uv sync --locked --group docs
uv run mkdocs build --strict
```
