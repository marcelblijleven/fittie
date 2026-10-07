# Components and accumulators

Fittie expands the native components defined by its bundled FIT profile,
including components selected through subfields. `decode()` keeps its existing
`list[FitFile]` API, and expanded values appear in each `DataMessage.fields` dictionary.

```python
from fittie import decode

for fitfile in decode("activity.fit"):
    for message in fitfile.get_messages_by_type("record"):
        print(message.fields.get("speed"), message.fields.get("distance"))
```

## How expansion works

A packed field's `bits`, `scale`, `offset`, and `accumulate` metadata describe its
components. In particular, a list of component scales must not be applied directly
to the containing byte array. Fittie reads the low-order bits first, across array
elements when needed, and stops when the container has insufficient remaining bits.
Wire endianness is resolved before component extraction.

For example, `compressed_speed_distance` contains two 12-bit values. Speed is in
hundredths of a metre per second; distance is in sixteenths of a metre. Distance is
a rolling counter. Its expansion also generates `enhanced_speed` through the
ordinary speed field's nested component.

Counter state belongs to a global message and destination field, with scale and
offset identifying the counter's units. It is shared across local definitions
within one FIT member and discarded at the next chained member or decode call.
Given `bits` bits, the next total is:

```text
total += (new_low_bits - total) & ((1 << bits) - 1)
```

An 8-bit counter going from 254 to 1 therefore produces 257. A directly encoded
full-width destination value seeds or resets the counter, after conversion into
the compressed counter's units. Raw-unit conversions use integer ratios so large
counters and nested scaling do not lose precision through intermediate floats.

Subfields are selected using reference values, including zero. All matching aliases
are exposed when multiple subfields match, as in workout repeat steps. The compiled
execution order accounts for references produced by other components. Repeated
components produce lists, and array destinations retain directly encoded values
followed by their expanded values. A valid directly encoded **scalar** destination
wins over a component targeting the same field; an invalid scalar may be filled
by expansion. This preserves enhanced fields' original precision.

The older `fittie_gearshifts.fit` fixture lacks an `event` selector, so its `data`
field cannot identify a gear-change subfield. The new synthetic tests encode valid
front/rear gear events and verify their four expanded fields.

The algorithm follows Garmin's [component and dynamic-field specification](https://developer.garmin.com/fit/articles/fit-protocol/fit_protocol.html)
and uses the [official SDK implementations](https://github.com/garmin/fit-python-sdk)
as additional references. The directly encoded scalar precedence above is an
explicit fittie policy; SDKs do not all resolve duplicate destinations identically.

## Performance design

Each local definition gets a reusable `struct.Struct` and field decoding plan.
Repeated messages read and unpack their native payload in one operation. Profile
metadata, bit masks, exact unit conversions, and component dependency order are
compiled once. Simple enhanced-field aliases bypass general bit extraction.
Accumulator values remain local to a decode, separate from cached profile plans.

Record headers and data messages use slots to reduce per-message allocations.
Their documented attributes remain accessible; arbitrary extra attributes cannot
be attached. The stream wrapper tracks its position rather than repeatedly asking
the buffered file object, and CRC calculation uses a byte table over each read
buffer. These changes preserve checksum and data-boundary validation.

## Measured results

Measured on Python 3.14.7 on September 30, 2026, against the working tree immediately
before this implementation. Inputs were preloaded into `BytesIO`, profile caches
were warmed, and each reported time is the median of five repeats of two complete
decodes, including output allocation. Garbage collection remained enabled.
These are local measurements, not universal performance guarantees.

| Input | CRC enabled before → after | CRC disabled before → after |
| --- | ---: | ---: |
| Synthetic native records, 20,000 messages | 179.08 → 102.60 ms | 112.57 → 87.48 ms |
| Synthetic packed records, 20,000 messages | 109.59 → 117.72 ms | 85.58 → 108.53 ms |
| Activity.fit, 3,611 messages | 54.22 → 27.02 ms | 32.84 → 21.01 ms |
| activity_lowbattery.fit, 4,001 messages | 103.63 → 45.42 ms | 70.46 → 36.96 ms |
| activity_poolswim_with_hr.fit, 4,590 messages | 36.18 → 28.91 ms | 22.74 → 25.12 ms |

With CRC enabled, the three Garmin samples improved by **1.25–2.28×**. The packed
synthetic case became about **7% slower** with CRC and **27% slower** without it:
the old decoder skipped component expansion entirely. HR-heavy decoding without
CRC also became about 10% slower in this run. The implementation now produces
additional values, so workload and output sizes differ from the baseline.

Peak traced memory for the three Garmin samples changed from 2.13/4.59/2.18 MiB
to 2.52/4.15/2.09 MiB. The packed synthetic case increased from 9.17 to 10.69 MiB
while retaining its additional decoded fields. Memory was measured separately
from timing. Raw results, input hashes, platform details, and source fingerprints
are in `benchmarks/components-python314.json` in the repository.

To reproduce the synthetic cases or add local samples:

```shell
uv run python scripts/benchmark_decode.py --memory --output /tmp/fittie-benchmark.json
uv run python scripts/benchmark_decode.py --files activity.fit --repeat 7 --loops 3
```

For an earlier source snapshot, use `--module-root /path/to/snapshot` with the same
Python interpreter and benchmark script. Timing thresholds are deliberately not
unit tests, since machine load and platform affect them.

## Correctness checks and boundaries

The full local suite passes 145 tests on each of Python 3.10–3.14. Ruff, mypy,
the strict documentation build, and sdist/wheel builds also pass.

Synthetic tests cover nested components, subfield selectors, repeated array
components, partial containers, invalid values, both byte orders, signed values,
large counters, exact scale conversion, full-value resets, local redefinitions,
compressed timestamps, and state isolation between files.

A separate comparison with `garmin-fit-sdk==21.217.0` found **zero differences across
50,787 component values** in 16 local Garmin samples, with enum/date conversion and
HR merging disabled in the reference decoder. Reproduce it with:

```shell
uv run --with garmin-fit-sdk==21.217.0 python scripts/compare_components.py tests/data/from_garmin_sdk
```

The Garmin SDK is not a runtime dependency. Its sample binaries remain optional
and untracked; synthetic regression tests run without them. Component expansion
is not HR-to-record merging or monitoring activity aggregation. Developer-field
component metadata and string component targets are not implemented. The bundled
profile is now 21.217.0; the original performance measurements above used 21.158.00.
The subsequent profile refresh retained those gains; see the compatibility audit.


The subsequent API completion adds string component targets, optional raw/expansion
modes, and preservation of native arrays for encoding. The benchmark table above
records the original component implementation; current results are recorded in
`benchmarks/features-python314.json`.
