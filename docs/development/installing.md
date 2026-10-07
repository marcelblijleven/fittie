# Installing

Fittie supports Python 3.10–3.14. Development uses Python 3.14, selected by
`.python-version`, and uv manages the virtual environment and dependencies.

```shell
uv sync --locked --all-groups
```

The package has no runtime dependencies. Development and documentation tools are
specified as dependency groups in `pyproject.toml` and resolved in `uv.lock`.
Use `uv run` for project commands. The old `requirements_dev.txt` and
`requirements_docs.txt` files have been replaced by these groups.

To test another supported interpreter without changing `.python-version`:

```shell
uv run --python 3.10 pytest
```

To build an sdist and wheel:

```shell
uv build
```
