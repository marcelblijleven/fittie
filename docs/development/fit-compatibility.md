# FIT compatibility audit

Reviewed September 30, 2026. Fittie now implements the FIT 2.0 codec and processing
features tracked by this audit against Garmin SDK/Profile 21.217.0. This includes
encoding, native components/counters and strings, developer data, streaming,
callbacks, enum/date conversion, HR merging, and common file-type validation.
Verification establishes interoperability for the tested cases; it is not device
certification or a guarantee about every malformed or vendor-specific file.

## Current Garmin references

- [FIT protocol specification](https://developer.garmin.com/fit/articles/fit-protocol/fit_protocol.html): binary layout, CRCs, definitions, compression, base types, and compatibility rules. Protocol 2.0 is distinct from the SDK/profile version.
- [SDK Tools 21.217.0](https://github.com/garmin/fit-sdk-tools/releases/tag/21.217.0): latest release checked, published September 22, 2026; the authoritative download for Profile.xlsx and FitCSVTool.
- [SDK distribution guide](https://developer.garmin.com/fit/get-the-sdk/): links to the separately distributed language SDKs and tools.
- [FIT file types](https://developer.garmin.com/fit/file-types/): file IDs and application-level message requirements.
- [Developer data cookbook](https://developer.garmin.com/fit/cookbook/developer-data/): FIT 2.0 developer metadata and fields.
- [Official Python SDK](https://github.com/garmin/fit-python-sdk): decoder options, component/subfield processing, heart-rate merging, and encoding. Its current README includes an encoder; the distribution landing page still says Python decoding only.

## Profile coverage

The bundled `__PROFILE_VERSION__` is **21.217.0**. It is generated directly from
Garmin's pinned workbook, with source URL and SHA-256 in `fittie/profile/source.json`.

| Measure | Before | Current |
| --- | ---: | ---: |
| Message definitions | 119 | 125 |
| Native field definitions | 1,382 | 1,566 |
| Types | 179 | 215 |

The refresh adds `training_settings` (13), `battery` (104), `pad` (105),
`nap_event` (412), `sleep_disruption_severity_period` (470), and
`sleep_disruption_overnight_severity` (471), plus 163 fields in existing messages.
There are 163 subfields in the current profile. References are resolved within
individual messages using enums from the same workbook, and accumulation metadata
is preserved for subfields.

`scripts/compare_profile.py` checks the generated metadata against
`garmin-fit-sdk==21.217.0`: all 125 messages, 1,566 fields, 163 subfields, and 215
types match apart from three documented differences in Garmin's own sources.
The workbook includes unused `avg_vam` bit widths in session/lap, and uses the
named `weight` type where the SDK uses `uint16`. Fittie retains the workbook values.
The fieldless `pad` message is derived from its enum because the workbook's
Messages sheet omits it. Unexpected comparison differences fail validation.

These counts describe profile coverage, not FIT conformance. Unknown messages and
fields still receive fallback names when their base types are understood. Developer
metadata and processing behavior are covered separately below.
See [generator instructions](scripts.md) for deterministic regeneration and CI checks.

## Feature assessment after these changes

The status below is a repository assessment based on code inspection and tests,
using the Garmin references above as the comparison baseline.

| Capability | Status | Evidence or limitation |
| --- | --- | --- |
| Headers and CRCs | Supported and hardened | Explicit little endian; signature/protocol/length checks; optional zero header CRC; 12/14-byte and extended headers; repeatable header encoding. |
| Message definitions and architecture | Supported | Local definitions, redefinitions, and big/little endian data; unknown messages and native fields retained under fallback names. |
| Chained FIT streams | Fixed | Member boundaries use stream positions, including CRC bytes; three-member and nonzero-start tests. |
| Truncation handling | Fixed | Incomplete headers, records, and CRCs raise errors even with CRC checks disabled; record reads cannot cross the data boundary. |
| Compressed timestamps | Implemented | Five-bit offsets, rollover, local types 0–3, full-timestamp resets, and per-member state. |
| Base types and arrays | Supported | All 17 base types, numeric/string arrays, invalid sentinels, and opaque future types; encoding tests cover each base type in both byte orders. |
| UTF-8 strings | Supported | Scalar strings, NUL-separated arrays, padding, invalid UTF-8 replacement, and string component targets. |
| Native scale and offset | Supported | Existing scalar/array transforms retained. |
| Subfields | Supported | Same-workbook references, zero-valued selectors, split subfields, and all matching aliases in workout repeat steps. |
| Component expansion | Supported | Packed scalars/arrays, nested and subfield components, partial containers, numeric scaling, and UTF-8 string destinations. |
| Accumulators | Implemented for native components | Modulo rollover, full-value seeds/resets, exact unit conversion, and state shared across local definitions but isolated per FIT member. |
| Developer fields | Supported per current protocol | Typed values and invalids, identity mappings, name collisions, preserved descriptor metadata, explicit native overrides, and opaque unknown data. See the protocol clarification below. |
| Semantic conversion | Supported, optional | Enum names, UTC dates, raw/scaled values, subfield/component switches; defaults retain numeric enums and timestamps. |
| HR message merging | Supported, optional | Anchors, fractional times, rollover, gap filling, duplicate records, interval averages, and the final interval. |
| File-type semantic validation | Supported, optional | Common File Id/developer rules plus the published Activity, Course, and Workout minimums; does not assert every vendor/sport rule. |
| Encoding | Supported | All base types, scale/offset inversion, enum/date inputs, strings/arrays, subfields, developers, explicit unknown fields, 16 local slots, both byte orders, CRCs, and chained output. |
| Streaming/callback APIs | Supported | `iter_messages` avoids collection retention; `iter_files` yields CRC-validated members; message and description listeners; nonseekable and short-read streams. |

## Developer-data protocol clarification

The earlier audit incorrectly treated applying native scale/offset and native
component machinery to developer data as missing required functionality.
[Garmin's protocol](https://developer.garmin.com/fit/articles/fit-protocol/fit_protocol.html)
specifies developer values at full precision and explicitly excludes native field
scaling. Fittie retains every descriptor entry, decodes values in their declared
base type, and exposes declared native equivalents only when requested. It does
not invent transformations from descriptor fields that the current SDK does not
apply. This is a correction to the assessment, not silent rescaling of user data.

## API completion and verification

The completed regression suite passed **263 tests on each of Python 3.10–3.14**.
The source distribution passed 247 tests with one optional sample skip; the wheel
passed encoding, decoding, strings, streaming, and validation smoke checks with no
runtime dependencies. Ruff, mypy, and the strict documentation build also passed.
See the validation history below for earlier milestones.

The public [API guide](../decoding.md) documents the new options, message identity,
encoding, streaming lifetime/CRC semantics, callbacks, and validation limits.
`FitFile.messages` and direct iteration follow wire order. Definitions survive
local-slot reuse; identical definitions and immutable headers are shared. Developer
identity keys are shared across records, with a compact mutable value mapping.

`scripts/compare_sdk.py` generates its baseline with Garmin's encoder, then checks
Fittie's values against Garmin decoding the original bytes, verifies that Garmin
accepts the re-encoded output, and checks full Fittie round trips. CI runs this
self-contained comparison. The optional local corpus run checks 17 files (the
synthetic file plus 16 Garmin samples), covering **163,199 values with zero
unexpected differences**. Separately, every field in all 22 available FIT fixtures
survives a round trip. The sample binaries remain optional; the core tests and CI
comparison do not depend on them.

HR behavior is independently tested at the final interval: Fittie applies its
average even when no subsequent sample arrives. The current Garmin helper can
omit that interval. This edge-case correction does not affect the checked sample
comparisons. String arrays extend the earlier first-NUL-only behavior.

Default-path timing and peak-memory results are recorded in
`benchmarks/features-python314.json`, comparing the preceding optimized 21.217.0
decoder with the completed APIs on Python 3.14. Optional conversions, merging,
validation, and encoding are separate from those default decode measurements.
With CRC enabled, four workloads stayed within 3% of the preceding decoder; the
pool-swim/HR workload improved by 18.8%. Measured peak memory changed by +2.1%
(Activity), −2.3% (low battery), and −3.6% (pool swim). These are local measurements,
not universal speed guarantees. Streaming avoids retaining decoded collections
when materialization is unnecessary.

## Python modernization

Development targets Python 3.14, retaining the public Python 3.10 minimum. CI covers
3.10–3.14. Packaging now uses an explicit Hatchling backend, SPDX license metadata,
and a `py.typed` marker. Dependency groups and the refreshed uv lockfile replace
the obsolete requirements files. Ruff owns formatting, import sorting, and typing
syntax modernization; mypy also checks unannotated function bodies.

UTC timestamp conversion uses timezone-aware `datetime.fromtimestamp`. Profile
conversion no longer relies on annotation strings, which differ with modern Python
annotation evaluation. The profile generator reads the workbook directly and produces deterministic
output without an external formatter. Documentation examples now match the list-returning 1.0 API.

## Validation history

Protocol fixtures and generator workbooks are self-contained. New tests cover
encoding all base types in both byte orders, opaque fields, developer identity and
missing metadata, string components, all matching aliases, streaming and CRC
failure timing, HR anchors/gaps/final intervals, and semantic validation.

Validation of the profile refresh:

- 170 tests passed on each of Python 3.10.13, 3.11.8, 3.12.6, 3.13.0, and 3.14.7.
- The built source distribution passed 154 tests with one optional sample-test skip.
  The wheel decoded every committed FIT fixture and contains no runtime dependencies.
- Ruff lint/format, mypy, strict documentation builds, and locked dependency checks pass.

- Generator tests use tiny temporary workbooks: stale/missing generated modules,
  message-local references, enum aliases, decimal scales, subfield accumulation,
  invalid metadata, and check mode are covered without network access.
- Binary regression tests cover all six added messages and split subfield selectors.
  Every bundled component/subfield plan compiles.
- Garmin metadata comparison: zero unexpected differences; three documented
  workbook/SDK differences as described above.
- Garmin sample comparison: 16 files, 50,787 component values, zero differences.
- Five full-decode benchmarks with CRC enabled changed by between −0.8% and +1.9%
  after the refresh (Python 3.14.7; median of five runs, two decodes per run).
  Raw measurements are in `benchmarks/profile-python314.json`. They compare the
  preceding optimized decoder with the refreshed profile, not the original decoder.

Validation of the initial Python modernization, before component implementation:

- 110 tests passed on each of Python 3.10.13, 3.11.8, 3.12.6, 3.13.0, and 3.14.7,
  including 16 local Garmin sample smoke tests.
- The built sdist passed 94 tests with one optional sample-test skip, confirming
  that the regression suite works without the ignored Garmin binaries.
- Ruff lint/format checks, mypy, and `mkdocs build --strict` passed.
- The sdist and wheel built successfully; an isolated installed-wheel smoke test
  decoded a chained fixture, and the wheel contains the typing marker.

This audit does not claim certification, complete device coverage, byte-for-byte
reproduction of input files, or validation of private vendor-specific semantics.

See [Components and accumulators](components.md) for the subsequent component
implementation, comparison against Garmin, and measured performance changes.
