## Unreleased

- Add profile-aware FIT 2.0 encoding, definition reuse, developer fields, and chained output.
- Preserve wire order and original definitions; add streaming and processing callbacks.
- Support string arrays and string component targets, all matching subfields, optional raw values and enum/date conversion, and HR merging.
- Retain opaque unknown fields and developer identities; add explicit native overrides and common file-type validation.
- Share immutable headers and repeated definitions, keeping the default decode path fast.
- Add full-value Garmin interoperability checks and encoder regression tests.

- Regenerate Garmin profile 21.217.0: 125 messages, 1,566 fields, 163 subfields, and 215 types.
- Replace CSV generation with deterministic workbook parsing, same-source enums/references, source provenance, and a check mode.
- Validate generated metadata against Garmin’s matching Python SDK; retain documented workbook differences.

- Expand native numeric components and subfields, including nested and array components.
- Accumulate rolling counters across local definitions, with exact scaling and full-value resets.
- Compile binary message plans, reduce record allocations, and accelerate CRC and stream-position tracking.
- Add repeatable performance benchmarks and an optional Garmin component comparison.

- Target Python 3.14 for development; retain support and CI for Python 3.10–3.14.
- Add explicit package builds, modern dependency groups, refreshed tooling, and typing metadata.
- Decode compressed timestamps; fix chained-file boundaries, CRC handling, and truncation errors.
- Fix zero-valued arrays, invalid floats, scalar strings, and file-type detection.
- Keep caller-provided streams open and modernize UTC datetime conversion.
- Document remaining FIT coverage gaps against Garmin SDK 21.217.0.

## v1.0.0 (2025-04-01)

### Features ✨

- add support for chained fitfiles (#32)

## v0.10.0 (2025-03-31)

### Features ✨

- use dataclasses, fix type errors

## v0.9.1 (2025-03-30)

## v0.9.0 (2025-03-30)

### Bugfixes 🐛

- handle unknown messages and fields

### Features ✨

- **profile**: add support for profile version 21.158.00

## v0.8.1 (2023-03-07)

### Bugfixes 🐛

- add type annotations from future to make it python 3.8 compatible

## v0.8.0 (2023-03-07)

### Bugfixes 🐛

- scale is not applied correctly to subfields
- add type annotations from future for 3.8 compatibility

### Features ✨

- add enrich data util
- add gear change data util

### refactor

- simplify decoding of messages, rename read_record to read_message
- move fitfile related utils to fitfile package

## v0.7.0 (2023-03-02)

### Features ✨

- apply scale and offset
- implement subfields
- add subfields to profile
- update fit profile to version 21.105

### refactor

- move decode to own file, field profile and subfield out of message profile

## v0.6.0 (2023-03-01)

### Features ✨

- add available fields property

## v0.5.0 (2023-02-27)

### Features ✨

- add filtering to iterating over fitfile

## v0.4.0 (2023-02-26)

### Features ✨

- add iterable mixin

## 0.3.2 (2023-02-25)

### Bugfixes 🐛

- incorrect path comparison

## 0.3.1 (2023-02-25)

### Bugfixes 🐛

- don't use subscripted generic for isinstance check

## 0.3.0 (2023-02-24)

### Features ✨

- add crc calculation
- add crc check for file header

## 0.2.0 (2023-02-24)

### Features ✨

- add streamable and datastream
- add field description class
- replace ZoneInfo with timezone for 3.8 compatibility

## 0.1.1 (2023-02-22)

### Bugfixes 🐛

- remove duplicate pyproject.toml url key

## 0.1.0 (2023-02-22)

### Bugfixes 🐛

- remove ZoneInfo for 3.8 support
- use lru_cache instead of cache for 3.8 support
- add annotations
- add annotations
- add workaround for StrEnum on Python versions < 3.11

### Features ✨

- add initial version of fittie fitfile parsing
