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
