"""Compare bundled metadata with an independently installed garmin-fit-sdk.

The SDK is an optional verification dependency, never a fittie dependency.
Run with an SDK version matching fittie's __PROFILE_VERSION__.
"""

from __future__ import annotations

from fittie import __PROFILE_VERSION__
from fittie.profile.fit_types import FIT_TYPES
from fittie.profile.mesg_nums import MESG_NUMS
from fittie.profile.messages import MESSAGES


def values(value, default=None):
    if value is None:
        return [] if default is None else [default]
    if isinstance(value, str):
        return value.split(",")
    return value if isinstance(value, list) else [value]


def compare(reference: dict) -> list[str]:
    differences = []
    documented = []
    # These differences are present in Garmin's own 21.217.0 workbook/SDK.
    # Keep the workbook metadata; narrow expected pairs make drift fail loudly.
    known = (
        {
            "session.avg_vam bits": ([16], []),
            "lap.avg_vam bits": ([16], []),
            "weight_scale.weight type": ("weight", "uint16"),
        }
        if __PROFILE_VERSION__ == "21.217.0"
        else {}
    )

    def check(path, actual, expected):
        if actual != expected:
            target = (
                documented if known.get(path) == (actual, expected) else differences
            )
            target.append(f"{path}: {actual!r} != {expected!r}")

    version = reference["version"]
    check(
        "version",
        __PROFILE_VERSION__,
        ".".join(str(version[key]) for key in ("major", "minor", "patch")),
    )
    check("message numbers", MESG_NUMS, reference["types"]["mesg_num"])
    check("types", set(FIT_TYPES), set(reference["types"]))
    for name, field_type in FIT_TYPES.items():
        check(
            f"type {name}",
            {n: v.value_name for n, v in field_type.values.items()},
            reference["types"].get(name),
        )
    check("messages", set(MESSAGES), set(reference["messages"]))
    fields_checked = subfields_checked = 0
    for num, message in MESSAGES.items():
        if num not in reference["messages"]:
            continue
        expected_message = reference["messages"][num]
        check(f"message {num} name", message.name, expected_message["name"])
        check(
            f"{message.name} fields",
            set(message.fields),
            set(expected_message["fields"]),
        )
        by_name = {field.field_name: n for n, field in message.fields.items()}
        accumulated = set()
        for field in message.fields.values():
            for source in (field, *(field.subfields or ())):
                targets = values(source.components)
                flags = values(source.accumulate, 0)
                flags = flags * len(targets) if len(flags) == 1 else flags
                accumulated.update(
                    by_name[name] for name, flag in zip(targets, flags) if flag
                )
        for n, field in message.fields.items():
            if n not in expected_message["fields"]:
                continue
            expected = expected_message["fields"][n]
            path = f"{message.name}.{field.field_name}"
            fields_checked += 1
            check(path + " accumulated", n in accumulated, expected["is_accumulated"])
            check(
                path + " subfield count",
                len(field.subfields or ()),
                len(expected["sub_fields"]),
            )
            pairs = [
                (field, expected),
                *zip(field.subfields or (), expected["sub_fields"]),
            ]
            for source, target in pairs:
                prefix = f"{message.name}.{source.field_name}"
                check(prefix + " name", source.field_name, target["name"])
                check(prefix + " type", source.field_type, target["type"])
                if "base_type" in target:
                    base = (
                        FIT_TYPES[source.field_type].base_type
                        if source.field_type in FIT_TYPES
                        else "enum"
                        if source.field_type == "bool"
                        else source.field_type
                    )
                    check(prefix + " base type", base, target["base_type"])
                    check(
                        prefix + " array",
                        bool(source.array) or base == "string",
                        target["array"] == "true",
                    )
                else:
                    check(prefix + " array", bool(source.array), bool(target["array"]))
                components = values(source.components)
                check(
                    prefix + " components",
                    [by_name[name] for name in components],
                    target["components"],
                )
                for key, default in (("scale", 1), ("offset", 0)):
                    actual = values(getattr(source, key), default)
                    if len(actual) == 1 and components:
                        actual *= len(components)
                    check(prefix + " " + key, actual, target[key])
                check(
                    prefix + " bits",
                    [int(v) for v in values(source.bits)],
                    target["bits"],
                )
                actual_units = values(source.units, "")
                actual_units += [""] * (len(components) - len(actual_units))
                check(prefix + " units", actual_units, values(target["units"], ""))
                if "map" in target:
                    subfields_checked += 1
                    actual_refs = [
                        (
                            r["field_number"],
                            r["field_name"],
                            r["value_number"],
                            r["value_name"],
                        )
                        for r in source.refs
                    ]
                    expected_refs = [
                        (r["num"], r["name"], r["raw_value"], r["value_name"])
                        for r in target["map"]
                    ]
                    check(prefix + " references", actual_refs, expected_refs)
    print(
        f"Compared {len(MESSAGES)} messages, {fields_checked} fields, {subfields_checked} subfields, and {len(FIT_TYPES)} types: {len(differences)} unexpected differences."
    )
    for note in documented:
        print("Documented workbook/SDK difference: " + note)
    return differences


if __name__ == "__main__":
    from garmin_fit_sdk import Profile

    errors = compare(Profile)
    for error in errors:
        print(error)
    raise SystemExit(bool(errors))
