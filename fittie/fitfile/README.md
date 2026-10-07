# Fitfile

## Usage

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

## Integrity checks

Header and file CRCs are checked by default. `decode(source, calculate_crc=False)`
skips checksum verification but still validates the header and data boundaries.
Malformed or truncated FIT members raise `DecodeException`; complete earlier
members are not silently returned as a successful partial decode.
