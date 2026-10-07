"""Compare available Garmin sample component values with an optional reference SDK.

Example:
  uv run --with garmin-fit-sdk==21.217.0 python scripts/compare_components.py tests/data/from_garmin_sdk

The reference package is used only for this check, not by the fittie library.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any


def equal(left: Any, right: Any) -> bool:
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equal(a, b) for a, b in zip(left, right))
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-8)
    return left == right


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    files = sorted(args.directory.glob("*.fit"))
    if not files:
        parser.error("no .fit samples found; Garmin sample binaries are not tracked")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from garmin_fit_sdk import Decoder, Stream

    from fittie import decode
    from fittie.fitfile.components import get_profile_plan
    from fittie.profile.messages import MESSAGES

    targets = {
        profile.name: {
            component.target
            for field in get_profile_plan(number).fields.values()
            for expansion in (field.expansion, *(v.expansion for v in field.variants))
            if expansion is not None
            for component in expansion.components
        }
        for number, profile in MESSAGES.items()
    }
    count = differences = 0
    for file in files:
        reference, errors = Decoder(Stream.from_file(str(file))).read(
            convert_types_to_strings=False,
            convert_datetimes_to_dates=False,
            merge_heart_rates=False,
        )
        if errors:
            raise RuntimeError(f"{file}: reference decoder errors: {errors}")
        decoded = decode(file)
        if len(decoded) != 1:
            raise ValueError("this comparison expects single-member Garmin samples")
        ours = decoded[0]
        for name, fields in targets.items():
            left = ours.data_messages.get(name, [])
            right = reference.get(name + "_mesgs", [])
            if len(left) != len(right):
                raise ValueError(f"{file}: {name} message counts differ")
            for index, (message, expected) in enumerate(zip(left, right)):
                for field in sorted(fields):
                    a, b = message.fields.get(field), expected.get(field)
                    if a is None and b is None:
                        continue
                    count += 1
                    if not equal(a, b):
                        differences += 1
                        print(f"{file.name}: {name}[{index}].{field}: {a!r} != {b!r}")
    print(f"{len(files)} files, {count} component values, {differences} differences")
    if differences:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
