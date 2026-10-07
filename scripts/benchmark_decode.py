"""Repeatable full-file decode benchmarks, including a dependency-free synthetic corpus.

Run with `uv run python scripts/benchmark_decode.py`. Use --module-root to compare
an earlier source snapshot under the same interpreter, and --files for local FITs.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import statistics
import struct
import sys
import time
import tracemalloc
from io import BytesIO
from pathlib import Path
from typing import Any


def synthetic_corpus(count: int) -> dict[str, bytes]:
    from fittie.fitfile.crc import calculate_crc

    def wrap(data: bytes) -> bytes:
        header = struct.pack("<BBHI4s", 14, 32, 21158, len(data), b".FIT")
        header += struct.pack("<H", calculate_crc(header))
        body = header + data
        return body + struct.pack("<H", calculate_crc(body))

    # Record definition: timestamp, heart rate, speed, altitude, distance.
    native_definition = b"\x40\x00\x00\x14\x00\x05" + bytes(
        [253, 4, 0x86, 3, 1, 2, 6, 2, 0x84, 2, 2, 0x84, 5, 4, 0x86]
    )
    native = b"".join(
        struct.pack("<BIBHHI", 0, 1_000_000 + i, 120, 5000, 3000, i * 500)
        for i in range(count)
    )
    # Compressed speed/distance plus a cycles counter, both crossing rollovers.
    packed_definition = b"\x40\x00\x00\x14\x00\x02" + bytes([8, 3, 13, 18, 1, 2])
    packed = b"".join(
        b"\x00"
        + (500 | ((i * 80 & 4095) << 12)).to_bytes(3, "little")
        + bytes([i % 255])
        for i in range(count)
    )
    return {
        "synthetic_native": wrap(native_definition + native),
        "synthetic_components": wrap(packed_definition + packed),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--module-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--files", type=Path, nargs="*", default=[])
    parser.add_argument("--records", type=int, default=20_000)
    parser.add_argument("--repeat", type=int, default=7)
    parser.add_argument("--loops", type=int, default=3)
    parser.add_argument("--memory", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if min(args.records, args.repeat, args.loops) < 1:
        parser.error("records, repeat, and loops must be positive")
    sys.path.insert(0, str(args.module_root.resolve()))
    from fittie import decode

    corpus = synthetic_corpus(args.records)
    corpus.update((str(path), path.read_bytes()) for path in args.files)
    results: list[dict[str, Any]] = []
    for name, payload in corpus.items():
        for crc in (True, False):
            # Warm imports/profile caches. Each call still constructs new file state
            # and message definitions, and materializes all output messages.
            result = decode(BytesIO(payload), calculate_crc=crc)
            messages = sum(
                len(group) for file in result for group in file.data_messages.values()
            )
            del result
            samples = []
            for _ in range(args.repeat):
                gc.collect()
                start = time.perf_counter()
                for _ in range(args.loops):
                    decode(BytesIO(payload), calculate_crc=crc)
                samples.append((time.perf_counter() - start) / args.loops)
            median = statistics.median(samples)
            row = {
                "name": name,
                "crc": crc,
                "messages": messages,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "median_ms": median * 1000,
                "min_ms": min(samples) * 1000,
                "messages_per_second": messages / median,
            }
            if args.memory:
                gc.collect()
                tracemalloc.start()
                result = decode(BytesIO(payload), calculate_crc=crc)
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                del result
                row["peak_bytes"] = peak
            results.append(row)
            print(
                f"{name:48} CRC={str(crc):5} {median * 1000:9.2f} ms {messages / median:12,.0f} messages/s"
            )
    if args.output:
        args.output.write_text(
            json.dumps(
                {
                    "python": sys.version,
                    "platform": platform.platform(),
                    "module_root": str(args.module_root.resolve()),
                    "repeat": args.repeat,
                    "loops": args.loops,
                    "results": results,
                },
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
