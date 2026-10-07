# Decoding

Decoding a FIT file can be done with the `decode` function from the Fittie package.
It accepts file paths and binary streams. The same package also provides encoding,
streaming, optional processing, and semantic validation.

- A path to file
- A file, opened in `rb` mode. E.g a BufferedReader
- A Streamable variable (more information about this later)

## Sources

### Path to file

```python
from fittie import decode

fitfiles = decode("/path/to/fit/file.fit")
```

By providing a path to a file, the file will be automatically opened in `rb` mode and
closed when the decoding is finished. If the provided file path does not exist, a
FileNotFound error will be raised.

### File

```python
from fittie import decode

with open("/path/to/fit/file.fit", "rb") as file:
    fitfiles = decode(file)
```

When providing an open file, the mode will be checked. If it is not `rb`, an IOError will
be raised. Caller-provided streams remain open; the caller is responsible for closing
them. Only streams opened by the decoder from a path are closed automatically.

### Streamable

```python
from io import BytesIO
from fittie import decode

data = BytesIO(b"example byte string")
fitfiles = decode(data)
```

The decoder accepts objects with a binary `read(size)` method, including nonseekable
streams and streams that return short reads. When available, `tell()` supplies the
initial position; otherwise the decoder tracks bytes from zero. Caller-owned streams
remain open.

## Crc

A crc will be calculated by default for each byte that is read during decoding, this
calculated crc is then checked against the crc at the end of the FIT file. To make the
avoid checksum computation, the crc check can be disabled.

> ⚠️ Disabling the crc check means the decoder can't verify if all the data is correct.

```python
fitfiles = decode("/path/to/fit/file.fit", calculate_crc=False)
```

## FitFile

The return type of `decode` is `list[FitFile]`, including one entry per chained member. This class exposes several methods
and properties which the user can access, like a collection of list of `DataMessage`.

More information about iteration over these lists of `DataMessage` can be found [here](iterating_data.md).

## Decode file type

If you're only interested in reading the file type, use the `decode_file_type` function.
It assumes the FIT file is encoded according to the protocol's best practices and begins
with the following structure:
* A file header
* A file_id definition message
* A file_id data message

If not, it will raise a `DecodeException` and no data will be returned.

```python
from fittie.fitfile.decode import decode_file_type

file_type = decode_file_type("/path/to/fit/file.fit")
```

Malformed or truncated data raises `DecodeException`, including when CRC validation
is disabled. An empty stream returns an empty list. See the
[FIT compatibility audit](development/fit-compatibility.md) for supported features.

Native numeric components and rolling counters are expanded automatically into
`DataMessage.fields`. Read [Components and accumulators](development/components.md)
for scaling, counter resets, duplicate-field handling, and performance measurements.


## Optional processing

Defaults retain numeric enum and timestamp values and apply native scales,
subfields, components, and counters. Change them with `DecodeOptions`:

```python
from fittie import DecodeOptions, decode

options = DecodeOptions(
    convert_types_to_strings=True,
    convert_datetimes_to_dates=True,
    merge_heart_rates=True,
)
fitfiles = decode("activity.fit", options=options)
```

Date conversion produces timezone-aware UTC datetimes. Device-uptime values below
`0x10000000` remain numeric. Unknown enum values also remain numeric. Developer
metadata messages retain numeric identifiers regardless of conversion options.

Other options are `apply_scale_and_offset`, `expand_subfields`, `expand_components`,
and `apply_native_overrides`. The last is disabled by default; when enabled, a
contributor's declared native equivalent is populated with its developer value.
It requires scaled native values. HR merging requires scaling and components.

HR merging expands anchored HR samples, carries previous rates across gaps for up
to five seconds in 250 ms steps, and averages samples between record timestamps.
Duplicate record timestamps reuse the last consumed sample. The last interval is
included even when no later sample exists; existing HR is retained in empty intervals.

String fields return a string, a list for NUL-separated string arrays, or `None`
for an invalid/empty field. Trailing NUL padding is discarded. Invalid UTF-8 is
replaced. This extends the earlier first-NUL-only behavior. String component targets
are assembled as UTF-8 bytes without numeric scaling.

## Streaming and callbacks

```python
from fittie import iter_files, iter_messages

for message in iter_messages("activity.fit"):
    print(message.definition.global_message_type, message.fields)

for fitfile in iter_files("chained.fit"):
    print(len(fitfile.messages))
```

`iter_messages` does not retain message collections. It preserves wire order and
checks the CRC at the end of each member; messages yielded before that point are
provisional. Exhaust the iterator to verify the entire stream. If stopping early,
call its `close()` method (or use `contextlib.closing`) to close files it opened.
`iter_files` buffers one member at a time and yields it after its CRC passes.
HR merging requires `decode` or `iter_files`, because HR data may follow records.

`message_listener(number, fields)` is an optional callback on all three entry
points. It sees mutable fields after requested conversions. With HR merging it
runs after the member is complete; otherwise it runs as messages are read, before
the final CRC is known. `field_description_listener(description, developer_info)`
runs when a developer description is registered.

## Message identity and developer data

`FitFile.messages` retains data messages in wire order; `data_messages` remains the
mapping of message names to lists. Each `DataMessage.definition` retains the
correct original definition, even when local slots are reused. Immutable record
headers and identical definitions are shared to reduce allocation and memory use.

`DataMessage.developer_fields` is a mutable mapping keyed by
`(developer_data_index, field_definition_number)`, or `None` when absent. Its values
are also exposed under friendly names in `fields`. Collisions receive a prefix
such as `developer_0_1_heart_rate`; native values are never silently overwritten.
Edit the identity mapping when re-encoding developer values. Friendly entries in
`fields` remain the decoded snapshot; editing one representation does not update
the other automatically.

Developer values are decoded in their declared base type, with invalid sentinels
handled correctly. The current protocol specifies full-precision values: native
profile scales are not applied to them. All descriptor fields, including scale,
offset, components, and accumulation metadata, remain available in
`fitfile.developer_data[index]["fields"][number].metadata`. These descriptors do
not cause undocumented transformations. Missing descriptions and unknown base
types retain opaque `bytes`, preserving stream alignment and re-encoding ability.

## Encoding

```python
from datetime import datetime, timezone
from fittie import Encoder, decode, encode

writer = Encoder()
writer.write(
    "file_id",
    {
        "type": "settings",
        "manufacturer": "development",
        "time_created": datetime.now(timezone.utc),
    },
)
writer.write("user_profile", {"friendly_name": "Example", "weight": 70.5})
payload = writer.finish("settings.fit")

# A FitFile or iterable of FitFiles can be encoded, including chained members.
files = decode("settings.fit")
encode(files, "copy.fit")
```

`Encoder.write` accepts physical values by default, enum numbers or names, aware
datetimes, numeric/string arrays, and `None` for invalid values. Use `raw=True`
for unscaled native values. Subfield names require matching selector fields.
Explicit `field_definitions` allow unknown/manufacturer messages and fields;
`endianness` accepts `"<"` or `">"`. `developer_fields` uses identity tuples and
requires preceding description messages for typed values; unknown descriptions
can be encoded as bytes. Explicit `developer_field_definitions` can retain sizes.

The encoder reuses all 16 local definition slots and writes a FIT 2.0 header,
normal timestamp records, and both CRCs. It validates values and sizes before
appending a message. `to_bytes()` and `finish()` are repeatable. Destination paths
are written only after the payload is complete; caller-owned output streams stay
open. The encoder buffers a member, while `encode(files)` buffers its output.

Re-encoding preserves values and order, not the original byte layout: compression,
local slot choices, padding, and headers may differ. Derived aliases are not
encoded a second time. The uncommon case of native arrays that also receive
expanded values retains the original array in `message.native_fields`; edit that
mapping to change the native array, or use `Encoder.write` to construct a new
message. String fields without a terminator are widened on re-encoding.

## Semantic validation

```python
from fittie import decode, validate

for fitfile in decode("activity.fit"):
    for issue in validate(fitfile):
        print(issue.code, issue.message_index, issue.message)
```

`FitFile.validate()` is equivalent. Structural decoding and CRC validation always
remain separate from these opt-in checks. The validator checks the common File Id
requirements, developer metadata ordering, and Garmin's published Activity,
Workout, and Course minimums: required messages/fields, counts, step references,
record chronology, and course timer boundaries. Other file types use the common
requirements because Garmin's profile does not prescribe their full message sets.

It returns all detected issues and never changes messages. This is an application
validator, not device certification or an exhaustive check of every sport/vendor
rule. Minimal SDK examples and interrupted recordings can decode correctly while
reporting missing summary data. Decode with HR merging when validating recordings
whose record values are supplied by separate HR messages.
