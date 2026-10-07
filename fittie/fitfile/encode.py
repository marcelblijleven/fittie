"""FIT 2.0 encoding with reusable local definitions and profile-aware values."""

from __future__ import annotations

import struct
from collections.abc import Iterable, Mapping
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, BinaryIO

from fittie.fitfile.crc import calculate_crc
from fittie.fitfile.field_definitions import DeveloperFieldDefinition, FieldDefinition
from fittie.fitfile.field_description import FieldDescription
from fittie.fitfile.processing import FIT_EPOCH
from fittie.profile.base_types import BASE_TYPES, BaseType
from fittie.profile.fit_types import FIT_TYPES
from fittie.profile.mesg_nums import MESG_NUMS
from fittie.profile.message_profile import SubField
from fittie.profile.messages import MESSAGES
from fittie.profile.version import PROFILE_VERSION

NUMBERS = {name: num for num, name in MESG_NUMS.items()}
BASE_NAMES = {base.name: base for base in BASE_TYPES.values()}


def _base(field_type: str) -> BaseType:
    name = (
        FIT_TYPES[field_type].base_type
        if field_type in FIT_TYPES
        else "enum"
        if field_type == "bool"
        else field_type
    )
    return BASE_NAMES[name]


def _string(value) -> bytes:
    if value is None:
        return b"\0"
    values = value if isinstance(value, list) else [value]
    if any(not isinstance(item, str) or "\0" in item for item in values):
        raise ValueError("string values must be strings without embedded NULs")
    return b"\0".join(item.encode("utf-8") for item in values) + b"\0"


def _raw(value, profile, scaled=True):
    if value is None:
        return None
    if isinstance(value, list):
        return [_raw(item, profile, scaled) for item in value]
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("FIT dates must be timezone-aware")
        value = int((value - FIT_EPOCH).total_seconds())
    if profile is None:
        return value
    if isinstance(value, str) and profile.field_type != "string":
        enum = FIT_TYPES.get(profile.field_type)
        names = {v.value_name: k for k, v in enum.values.items()} if enum else {}
        if value not in names:
            raise ValueError(f"unknown {profile.field_type} value: {value}")
        value = names[value]
    scale = profile.scale if isinstance(profile.scale, (int, float)) else 1
    offset = profile.offset or 0
    if scaled and isinstance(value, (int, float)) and (scale != 1 or offset != 0):
        value = (Decimal(str(value)) + Decimal(str(offset))) * Decimal(str(scale))
    return value


def _pack(value, base: BaseType | None, endian: str, size: int | None = None) -> bytes:
    if base is None or base.value_type is bytes:
        if not isinstance(value, bytes):
            raise ValueError("unknown base types require opaque bytes")
        payload = value
    elif base.value_type is str:
        payload = _string(value)
        if size is not None:
            if len(payload) > size:
                raise ValueError("string exceeds its field definition size")
            payload = payload.ljust(size, b"\0")
    else:
        values = value if isinstance(value, (list, tuple)) else [value]
        if size is not None and value is None:
            values = [None] * (size // base.size)
        chunks = []
        for item in values:
            if item is None:
                chunks.append(
                    b"\xff" * base.size
                    if base.value_type is float
                    else struct.pack(endian + base.fmt, base.invalid_value)
                )
                continue
            if base.value_type is int:
                item = (
                    int(round(item))
                    if isinstance(item, (float, Decimal))
                    else int(item)
                )
            else:
                item = float(item)
            try:
                chunks.append(struct.pack(endian + base.fmt, item))
            except (struct.error, OverflowError) as exc:
                raise ValueError(f"value does not fit {base.name}: {item}") from exc
        payload = b"".join(chunks)
    if not 1 <= len(payload) <= 255 or (size is not None and len(payload) != size):
        raise ValueError(
            "field payload must match its definition and contain 1..255 bytes"
        )
    return payload


class Encoder:
    """Build a FIT member from physical values (or raw values with raw=True).

    write() accepts profile message/field names, numeric enum values or names, and
    aware datetime objects. Explicit field definitions allow manufacturer fields.
    Developer fields are keyed by (developer_data_index, field_definition_number).
    Their description messages must be written first for typed encoding.
    """

    def __init__(self, *, profile_version: int | None = None):
        major, minor, _ = map(int, PROFILE_VERSION.split("."))
        self.profile_version = (
            major * 1000 + minor if profile_version is None else profile_version
        )
        self._data = bytearray()
        self._schemas: dict[tuple, int] = {}
        self._slots: dict[int, tuple] = {}
        self._next_slot = 0
        self._descriptions: dict[tuple[int, int], FieldDescription] = {}
        self._applications: dict[int, Any] = {}

    def write(
        self,
        message_type: str | int,
        fields: dict[str | int, Any],
        *,
        developer_fields: Mapping[tuple[int, int], Any] | None = None,
        field_definitions: Iterable[FieldDefinition] | None = None,
        developer_field_definitions: Iterable[DeveloperFieldDefinition] | None = None,
        endianness: str = "<",
        raw: bool = False,
    ) -> None:
        if endianness not in ("<", ">"):
            raise ValueError("endianness must be '<' or '>'")
        number = (
            NUMBERS.get(message_type) if isinstance(message_type, str) else message_type
        )
        if number is None or not 0 <= number <= 65535:
            raise ValueError(f"unknown message type: {message_type}")
        profile = MESSAGES.get(number)
        native: list[tuple[FieldDefinition, bytes]] = []
        if field_definitions is not None:
            for definition in field_definitions:
                field = profile.fields.get(definition.number) if profile else None
                name = (
                    field.field_name
                    if field
                    else {
                        250: "part_index",
                        253: "timestamp",
                        254: "message_index",
                    }.get(
                        definition.number,
                        f"{profile.name if profile else f'unknown_{number}'}_unknown_field_{definition.number}",
                    )
                )
                value = fields.get(definition.number, fields.get(name))
                native.append(
                    (
                        definition,
                        _pack(
                            _raw(value, field, not raw),
                            definition.base_type,
                            endianness,
                            definition.size,
                        ),
                    )
                )
        else:
            lookup: dict[Any, tuple[int, Any, Any]] = (
                {f.field_name: (n, f, None) for n, f in profile.fields.items()}
                if profile
                else {}
            )
            if profile:
                for n, f in profile.fields.items():
                    for sub in f.subfields or ():
                        lookup[sub.field_name] = (n, sub, f)
            seen = set()
            for key, value in fields.items():
                if isinstance(key, int) and profile and key in profile.fields:
                    n, field, parent = key, profile.fields[key], None
                elif key in lookup:
                    n, field, parent = lookup[key]
                else:
                    raise ValueError(
                        f"unknown field {key!r}; supply explicit field definitions"
                    )
                if n in seen:
                    raise ValueError(
                        f"multiple values for field {n}; choose parent or active subfield"
                    )
                seen.add(n)
                if parent is not None:
                    assert profile is not None and isinstance(field, SubField)
                    matches = any(
                        _raw(
                            fields.get(ref["field_name"]),
                            profile.fields[int(ref["field_number"])],
                            False,
                        )
                        == ref["value_number"]
                        for ref in field.refs
                        if ref is not None
                    )
                    if not matches:
                        raise ValueError(
                            f"subfield {key} does not match its reference fields"
                        )
                base = _base(parent.field_type if parent else field.field_type)
                payload = _pack(_raw(value, field, not raw), base, endianness)
                native.append((FieldDefinition(n, len(payload), base), payload))
        developers: list[tuple[DeveloperFieldDefinition, bytes]] = []
        explicit = {
            (d.data_index, d.number): d for d in developer_field_definitions or ()
        }
        for developer_key, value in (developer_fields or {}).items():
            index, num = developer_key
            if not 0 <= index <= 254 or not 0 <= num <= 254:
                raise ValueError("developer index and field number must be 0..254")
            description = self._descriptions.get(developer_key)
            dev_definition = explicit.get(developer_key)
            payload = _pack(
                value,
                description.base_type if description else None,
                endianness,
                dev_definition.size if dev_definition else None,
            )
            developers.append(
                (
                    dev_definition
                    or DeveloperFieldDefinition(num, len(payload), index),
                    payload,
                )
            )
        if set(explicit) - (developer_fields or {}).keys():
            raise ValueError("missing developer values for explicit definitions")
        if len({d.number for d, _ in native}) != len(native):
            raise ValueError("duplicate native field definition")
        if len(native) > 255 or len(developers) > 255:
            raise ValueError("too many fields in message definition")
        for definition, _ in native:
            if (
                not 0 <= definition.number <= 254
                or not 0 <= definition.wire_type <= 255
            ):
                raise ValueError("field number must be 0..254")
        # Prepare all bytes before changing encoder state.
        schema = (
            number,
            endianness,
            tuple((d.number, d.size, d.wire_type) for d, _ in native),
            tuple((d.number, d.size, d.data_index) for d, _ in developers),
        )
        local = self._schemas.get(schema)
        if local is None:
            local = self._next_slot
            self._next_slot = (local + 1) % 16
            previous = self._slots.get(local)
            if previous is not None:
                del self._schemas[previous]
            self._slots[local] = schema
            self._schemas[schema] = local
            self._data += bytes(
                [0x40 | (0x20 if developers else 0) | local, 0, int(endianness == ">")]
            )
            self._data += struct.pack(endianness + "H", number) + bytes([len(native)])
            for d, _ in native:
                self._data += bytes([d.number, d.size, d.wire_type])
            if developers:
                self._data += bytes([len(developers)])
                for dev_def, _ in developers:
                    self._data += bytes(
                        [dev_def.number, dev_def.size, dev_def.data_index]
                    )
        self._data.append(local)
        self._data += b"".join(payload for _, payload in (*native, *developers))
        if number == 207:
            application_index = fields.get("developer_data_index", fields.get(3))
            application = fields.get("application_id", fields.get(1))
            if isinstance(application_index, int):
                previous = self._applications.get(application_index)
                if previous is not None and previous != application:
                    self._descriptions = {
                        key: value
                        for key, value in self._descriptions.items()
                        if key[0] != application_index
                    }
                self._applications[application_index] = application
        if number == 206:
            assert profile is not None
            metadata = {
                profile.fields[k].field_name if isinstance(k, int) else k: v
                for k, v in fields.items()
            }
            # Allow fit_base_type_id enum names, as with all profile fields.
            if isinstance(metadata.get("fit_base_type_id"), str):
                metadata["fit_base_type_id"] = _raw(
                    metadata["fit_base_type_id"], profile.fields[2], False
                )
            if isinstance(metadata.get("developer_data_index"), int) and isinstance(
                metadata.get("field_definition_number"), int
            ):
                description = FieldDescription(**metadata)
                self._descriptions[
                    (
                        description.developer_data_index,
                        description.field_definition_number,
                    )
                ] = description

    def to_bytes(self) -> bytes:
        header = struct.pack(
            "<BBHI4s", 14, 0x20, self.profile_version, len(self._data), b".FIT"
        )
        header += struct.pack("<H", calculate_crc(header))
        content = header + self._data
        return content + struct.pack("<H", calculate_crc(content))

    def finish(self, destination: str | Path | BinaryIO | None = None) -> bytes:
        payload = self.to_bytes()
        _write_destination(destination, payload)
        return payload


def _write_destination(destination, payload):
    if isinstance(destination, (str, Path)):
        Path(destination).write_bytes(payload)
    elif destination is not None:
        written = destination.write(payload)
        if written is not None and written != len(payload):
            raise OSError("destination accepted only part of the FIT data")


def encode(files, destination: str | Path | BinaryIO | None = None) -> bytes:
    """Encode a FitFile or iterable of FitFiles into a (possibly chained) stream.

    Only the original native definitions are encoded; derived component/subfield
    aliases are not written twice. Message order and developer identities survive.
    """
    from fittie.fitfile.fitfile import FitFile

    if isinstance(files, FitFile):
        files = [files]
    members = []
    for file in files:
        encoder = Encoder(profile_version=file.header.profile_version)
        for message in file.messages:
            definition = message.definition
            if definition is None:
                raise ValueError(
                    "encoding a DataMessage requires its original definition; use Encoder.write for new messages"
                )
            fields = (
                {**message.fields, **message.native_fields}
                if message.native_fields
                else message.fields
            )
            native = list(definition.field_definitions)
            if "timestamp" in fields and not any(d.number == 253 for d in native):
                native.insert(0, FieldDefinition(253, 4, BASE_TYPES[0x86]))
            profile = MESSAGES.get(definition.global_message_type)
            for i, field_def in enumerate(native):
                if field_def.base_type.value_type is str:
                    field = profile.fields.get(field_def.number) if profile else None
                    name = (
                        field.field_name
                        if field
                        else f"unknown_{definition.global_message_type}_unknown_field_{field_def.number}"
                    )
                    size = max(field_def.size, len(_string(fields.get(name))))
                    native[i] = FieldDefinition(
                        field_def.number, size, field_def.base_type, field_def.wire_type
                    )
            encoder.write(
                definition.global_message_type,
                fields,
                field_definitions=native,
                developer_field_definitions=definition.developer_field_definitions,
                developer_fields=message.developer_fields,
                endianness=definition.endianness,
                raw=not definition.options.apply_scale_and_offset,
            )
        members.append(encoder.to_bytes())
    payload = b"".join(members)
    _write_destination(destination, payload)
    return payload
