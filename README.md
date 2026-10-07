# fittie

Read and write Garmin FIT files with a dependency-free Python library. Requires Python 3.10 or newer; development and CI include Python 3.14.

[![PyPI version](https://img.shields.io/pypi/v/fittie?color=green)](https://pypi.org/project/fittie/)

## Installation

```shell
pip install fittie
```

## Example

`decode()` returns a list of `FitFile` objects, including one object for each member of a chained FIT stream.

```python
from fittie import decode

for fitfile in decode("path/to/activity.fit"):
    print(fitfile.file_type)
    for record in fitfile.get_messages_by_type("record"):
        print(record.fields.get("timestamp"), record.fields.get("heart_rate"))
```

See [the documentation](https://marcelblijleven.github.io/fittie/) for filtering and analysis examples.

<!-- fitfile section -->
## Fitfile

### Usage

Pass a path (`str` or `pathlib.Path`) or a binary stream to `decode`.
Paths are opened and closed automatically; caller-provided streams remain open.

```python
from fittie import decode

with open("path/to/activity.fit", "rb") as source:
    fitfiles = decode(source)

for fitfile in fitfiles:
    print(fitfile.available_message_types)
    records = fitfile.get_messages_by_type("record")
    for record in records:
        print(record.fields)
```

`fitfile.data_messages` groups `DataMessage` objects by message name. Iterating a
`FitFile` directly yields field dictionaries. The `file_type` property reads the
`file_id` message; ordinary field values retain numeric enum and timestamp values.

### Integrity checks

Header and file CRCs are checked by default. `decode(source, calculate_crc=False)`
skips checksum verification but still validates the header and data boundaries.
Malformed or truncated FIT members raise `DecodeException`; complete earlier
members are not silently returned as a successful partial decode.

<!-- end fitfile section -->

## FIT compatibility

The bundled profile is **[21.217.0](https://github.com/garmin/fit-sdk-tools/releases/tag/21.217.0)**,
the latest Garmin SDK Tools release checked on September 30, 2026.
Fittie supports native components and counters, developer data, string arrays,
chained files, compressed timestamp decoding, encoding, optional enum/date
conversions, HR merging, streaming, callbacks, and common file-type validation.

```python
from fittie import Encoder, encode, iter_messages, validate

for message in iter_messages("activity.fit"):
    print(message.fields)

files = decode("activity.fit")
encode(files, "copy.fit")
issues = validate(files[0])
```

See the [API guide](docs/decoding.md) for options and encoding examples, and the
[compatibility audit](docs/development/fit-compatibility.md) for scope, independent
Garmin comparisons, and measured performance. Interoperability is tested against
Garmin SDK 21.217.0; it is not a claim of device certification.

## Development

```shell
uv sync --locked --all-groups
uv run pytest
uv run mypy fittie
uv run ruff check .
uv run ruff format --check .
uv build
```

Dependencies and tool configuration live in `pyproject.toml`; `uv.lock` records
resolved versions. See [development setup](docs/development/installing.md).
