"""Generate the bundled FIT profile directly from Garmin's Profile.xlsx.

No imports from fittie: regeneration must work with stale or missing generated files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
BASE_TYPES = {
    "enum",
    "sint8",
    "uint8",
    "sint16",
    "uint16",
    "sint32",
    "uint32",
    "string",
    "float32",
    "float64",
    "uint8z",
    "uint16z",
    "uint32z",
    "byte",
    "sint64",
    "uint64",
    "uint64z",
}
TYPE_COLUMNS = ("Type Name", "Base Type", "Value Name", "Value", "Comment")
MESSAGE_COLUMNS = (
    "Message Name",
    "Field Def #",
    "Field Name",
    "Field Type",
    "Array",
    "Components",
    "Scale",
    "Offset",
    "Units",
    "Bits",
    "Accumulate",
    "Ref Field Name",
    "Ref Field Value",
    "Comment",
)


def sheet_rows(workbook: Any, name: str, columns: tuple[str, ...]):
    """Reject formulas instead of silently accepting missing/stale cached values."""
    rows = iter(workbook[name])
    header = [cell.value for cell in next(rows)]
    if any(header.count(column) != 1 for column in columns):
        raise ValueError(f"{name}: missing or duplicate required column")
    indexes = [header.index(column) for column in columns]
    for number, cells in enumerate(rows, 2):
        if any(cells[index].data_type == "f" for index in indexes):
            raise ValueError(f"{name}:{number}: formulas are not supported")
        row = {
            column: str(cells[index].value).strip()
            if cells[index].value is not None
            else ""
            for column, index in zip(columns, indexes)
        }
        if any(row.values()):
            yield number, row


def integer(value: str) -> int:
    return int(value, 16 if value.lower().startswith("0x") else 10)


def number(value: str) -> int | float:
    try:
        return integer(value)
    except ValueError:
        result = float(value)
        if not math.isfinite(result):
            raise ValueError(f"non-finite number: {value}") from None
        return result


def items(value: str) -> list[str]:
    return [part.strip() for part in value.split(",")] if value else []


def scalar_or_list(values: list) -> Any:
    return values[0] if len(values) == 1 else values or None


def parse_types(workbook: Any) -> dict:
    result: dict = {}
    current = None
    for line, row in sheet_rows(workbook, "Types", TYPE_COLUMNS):
        try:
            if name := row["Type Name"]:
                if name in result or row["Base Type"] not in BASE_TYPES:
                    raise ValueError(f"duplicate type or unknown base type: {name}")
                current = result[name] = {
                    "base_type": row["Base Type"],
                    "values": {},
                    "names": {},
                }
            elif row["Value Name"]:
                if current is None:
                    raise ValueError("enum value has no type")
                value = integer(row["Value"])
                if row["Value Name"] in current["names"]:
                    raise ValueError("duplicate enum name")
                # Garmin retains deprecated aliases. The last name is canonical;
                # all names remain available when resolving subfield references.
                current["names"][row["Value Name"]] = value
                current["values"][value] = {
                    "value_name": row["Value Name"],
                    "comment": row["Comment"] or None,
                }
            else:
                raise ValueError("unrecognized type row")
        except ValueError as exc:
            raise ValueError(f"Types:{line}: {exc}") from exc
    if "mesg_num" not in result:
        raise ValueError("Types: mesg_num is required")
    return result


def parse_field(row: dict[str, str], types: dict) -> dict:
    name, field_type = row["Field Name"], row["Field Type"]
    if not name or field_type not in BASE_TYPES | types.keys() | {"bool"}:
        raise ValueError(
            f"missing field name or unknown field type: {name}/{field_type}"
        )
    array = row["Array"]
    if array and not re.fullmatch(r"\[(N|[1-9][0-9]*)\]", array):
        raise ValueError(f"invalid array size: {array}")
    result: dict = {"field_name": name, "field_type": field_type}
    if array:
        result["array"] = "N" if array == "[N]" else integer(array[1:-1])
    for key, column in (
        ("components", "Components"),
        ("units", "Units"),
        ("comment", "Comment"),
    ):
        if value := row[column]:
            result[key] = scalar_or_list(items(value)) if key == "components" else value
    for key, column in (("scale", "Scale"), ("accumulate", "Accumulate")):
        if row[column]:
            values = [
                number(v) if key == "scale" else integer(v) for v in items(row[column])
            ]
            if key == "scale" and any(v == 0 for v in values):
                raise ValueError("scale must be nonzero")
            if key == "accumulate" and any(v not in (0, 1) for v in values):
                raise ValueError("accumulate must be 0 or 1")
            result[key] = scalar_or_list(values)
    if row["Offset"]:
        result["offset"] = number(row["Offset"])
    if row["Bits"]:
        widths = [integer(v) for v in items(row["Bits"])]
        if any(not 1 <= width <= 64 for width in widths):
            raise ValueError("component bit width must be between 1 and 64")
        result["bits"] = widths[0] if len(widths) == 1 else ",".join(map(str, widths))
    return result


def parse_messages(workbook: Any, types: dict) -> dict:
    numbers = {v["value_name"]: k for k, v in types["mesg_num"]["values"].items()}
    result: dict = {}
    group = None
    message = field = None
    for line, row in sheet_rows(workbook, "Messages", MESSAGE_COLUMNS):
        try:
            if name := row["Message Name"]:
                if name not in numbers or numbers[name] in result:
                    raise ValueError(f"unknown or duplicate message: {name}")
                message = result[numbers[name]] = {
                    "name": name,
                    "fields": {},
                    "group": group,
                }
                field = None
            elif not row["Field Name"] and row["Field Type"].isupper():
                group = row["Field Type"]
                message = field = None
            else:
                if message is None:
                    raise ValueError("field has no message")
                parsed = parse_field(row, types)
                if row["Field Def #"]:
                    num = integer(row["Field Def #"])
                    if not 0 <= num <= 254 or num in message["fields"]:
                        raise ValueError(f"invalid or duplicate field number: {num}")
                    parsed["subfields"] = []
                    message["fields"][num] = field = parsed
                else:
                    if field is None:
                        raise ValueError("subfield has no parent field")
                    names, values = (
                        items(row["Ref Field Name"]),
                        items(row["Ref Field Value"]),
                    )
                    if not names or len(names) != len(values):
                        raise ValueError(
                            "subfield reference names and values must match"
                        )
                    parsed.update(
                        ref_field_name=scalar_or_list(names),
                        ref_field_value=scalar_or_list(values),
                    )
                    field["subfields"].append(parsed)
        except ValueError as exc:
            raise ValueError(f"Messages:{line}: {exc}") from exc
    # The SDK has a fieldless padding message; its enum is in Types but it
    # has no row in Messages. Do not invent definitions for other missing types.
    if "pad" in numbers:
        result.setdefault(numbers["pad"], {"name": "pad", "fields": {}, "group": None})
    for message in result.values():
        resolve_message(message, types)
    return result


def as_list(value: Any) -> list:
    return value if isinstance(value, list) else [value]


def resolve_message(message: dict, types: dict) -> None:
    """Resolve references only after every field in this message has been read."""
    fields = {f["field_name"]: (n, f) for n, f in message["fields"].items()}
    if len(fields) != len(message["fields"]):
        raise ValueError(f"{message['name']}: duplicate field name")
    dependencies: dict[str, set[str]] = {name: set() for name in fields}
    for field in message["fields"].values():
        for sub in field["subfields"]:
            refs = []
            for name, value in zip(
                as_list(sub["ref_field_name"]), as_list(sub["ref_field_value"])
            ):
                if name not in fields:
                    raise ValueError(
                        f"{message['name']}: unknown reference field {name}"
                    )
                num, target = fields[name]
                names = types.get(target["field_type"], {}).get("names", {})
                try:
                    raw_value = names[value] if value in names else integer(value)
                except ValueError as exc:
                    raise ValueError(
                        f"{message['name']}: unresolved reference {name}={value}"
                    ) from exc
                refs.append(
                    {
                        "field_number": num,
                        "value_number": raw_value,
                        "value_name": value,
                        "field_name": name,
                    }
                )
                dependencies[field["field_name"]].add(name)
            sub["refs"] = refs
        for source in (field, *field["subfields"]):
            if not source.get("components"):
                continue
            targets = as_list(source["components"])
            for key in ("bits", "scale", "accumulate"):
                value = source.get(key)
                values = items(value) if isinstance(value, str) else as_list(value)
                if (key == "bits" and value is None) or len(values) not in (
                    1,
                    len(targets),
                ):
                    raise ValueError(
                        f"{message['name']}: inconsistent {key} for {source['field_name']}"
                    )
            for target in targets:
                if target not in fields:
                    raise ValueError(
                        f"{message['name']}: unknown component target {target}"
                    )
                dependencies[target].add(field["field_name"])
    tuple(TopologicalSorter(dependencies).static_order())


def constructor(name: str, attributes: dict, **expressions: str) -> str:
    arguments = [
        f"{key}={expressions.get(key, repr(value))}"
        for key, value in attributes.items()
    ]
    return f"{name}({', '.join(arguments)})"


def render(workbook_path: Path, version: str) -> dict[str, str]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("version must have major.minor.patch format")
    with workbook_path.open("rb") as source:
        digest = hashlib.sha256(source.read()).hexdigest()
    workbook = load_workbook(workbook_path, read_only=True, data_only=False)
    try:
        types = parse_types(workbook)
        messages = parse_messages(workbook, types)
    finally:
        workbook.close()
    numbers = {n: v["value_name"] for n, v in types["mesg_num"]["values"].items()}
    header = f"# Generated from Garmin FIT Profile {version}; do not edit.\n# Source and SHA-256: source.json. Regenerate with scripts/parse_profile.py.\n\n"
    type_lines = [
        header,
        "from .field_type import FieldType, FieldTypeValue\n\n",
        "FIT_TYPES: dict[str, FieldType] = {\n",
    ]
    for name, value in types.items():
        values = (
            "{\n"
            + "".join(
                f"        {n}: {constructor('FieldTypeValue', v)},\n"
                for n, v in value["values"].items()
            )
            + "    }"
        )
        type_lines.append(
            f"    {name!r}: {constructor('FieldType', {k: value[k] for k in ('base_type', 'values')}, values=values)},\n"
        )
    type_lines.append("}\n")
    message_lines = [
        header,
        "from .message_profile import FieldProfile, MessageProfile, SubField\n\n",
        "MESSAGES: dict[int, MessageProfile] = {\n",
    ]
    for num, message in sorted(messages.items()):
        field_lines = ["{\n"]
        for n, field in message["fields"].items():
            subs = (
                "["
                + ", ".join(constructor("SubField", sub) for sub in field["subfields"])
                + "]"
            )
            field_lines.append(
                f"        {n}: {constructor('FieldProfile', field, subfields=subs)},\n"
            )
        field_lines.append("    }")
        message_lines.append(
            f"    {num}: {constructor('MessageProfile', message, fields=''.join(field_lines))},\n"
        )
    message_lines.append("}\n")
    metadata = {
        "version": version,
        "source_url": f"https://github.com/garmin/fit-sdk-tools/releases/download/{version}/Profile.xlsx",
        "sha256": digest,
        "messages": len(messages),
        "fields": sum(len(m["fields"]) for m in messages.values()),
        "subfields": sum(
            len(f["subfields"]) for m in messages.values() for f in m["fields"].values()
        ),
        "types": len(types),
    }
    outputs = {
        "fit_types.py": "".join(type_lines),
        "messages.py": "".join(message_lines),
        "mesg_nums.py": header
        + "MESG_NUMS: dict[int, str] = {\n"
        + "".join(f"    {n}: {name!r},\n" for n, name in sorted(numbers.items()))
        + "}\n",
        "version.py": header + f'PROFILE_VERSION = "{version}"\n',
        "source.json": json.dumps(metadata, indent=2) + "\n",
    }
    for name, content in outputs.items():
        if name.endswith(".py"):
            compile(content, name, "exec")
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument(
        "--version",
        required=True,
        help="SDK release version (the workbook does not contain it)",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT,
        help="repository root; defaults to this script's repository",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if generated files differ, without writing",
    )
    args = parser.parse_args()
    try:
        outputs = render(args.workbook, args.version)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Profile generation failed: {exc}\n")
    directory = args.output_root / "fittie" / "profile"
    changed = [
        name
        for name, text in outputs.items()
        if not (directory / name).exists()
        or (directory / name).read_text(encoding="utf-8") != text
    ]
    if args.check:
        if changed:
            print("Out of date: " + ", ".join(changed))
            return 1
        print("Generated profile is up to date.")
        return 0
    directory.mkdir(parents=True, exist_ok=True)
    for name in changed:
        path = directory / name
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(outputs[name], encoding="utf-8")
        temporary.replace(path)
    print(f"Generated profile {args.version}: {len(changed)} files updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
