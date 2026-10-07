"""Binary decoding plans reused for every record with the same local definition."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from fittie.fitfile.components import (
    Accumulators,
    FieldPlan,
    apply_components,
    expansion_sources,
    get_profile_plan,
    transform,
)
from fittie.fitfile.strings import decode_string
from fittie.fitfile.utils.exceptions import DecodeException
from fittie.profile.util import get_message_profile

if TYPE_CHECKING:
    from fittie.fitfile.definition_message import DefinitionMessage
    from fittie.fitfile.utils.datastream import Streamable


@dataclass(frozen=True, slots=True)
class FieldReader:
    name: str
    index: int
    count: int
    offset: int
    size: int
    invalid: int
    kind: int
    plan: FieldPlan | None


class MessageDecoder:
    """One native payload read/unpack; no profile lookup in the field loop."""

    def __init__(self, definition: DefinitionMessage, compressed: bool = False):
        self.options = definition.options
        profile = get_message_profile(definition.global_message_type)
        self.profile_plan = get_profile_plan(definition.global_message_type)
        self.readers: list[FieldReader] = []
        sources = []
        fmt = definition.endianness
        index = offset = 0
        for field in definition.field_definitions:
            if compressed and field.number == 253:
                continue
            base = field.base_type
            if field.size == 0 or field.size % base.size:
                raise DecodeException(
                    detail="invalid field size for base type", position=0
                )
            field_profile = profile.fields.get(field.number) if profile else None
            name = (
                field_profile.field_name
                if field_profile
                else (
                    {253: "timestamp", 254: "message_index", 250: "part_index"}[
                        field.number
                    ]
                    if field.number in (250, 253, 254)
                    else f"{profile.name if profile else f'unknown_{definition.global_message_type}'}_unknown_field_{field.number}"
                )
            )
            plan = (
                self.profile_plan.fields.get(name)
                if base.value_type is not bytes
                else None
            )
            if plan is not None and not self.options.apply_scale_and_offset:
                plan = replace(plan, scale=1, offset=0)
            if plan is not None and (plan.expansion is not None or plan.variants):
                sources.append(plan)
            count = field.size // base.size
            is_string = base.value_type in (str, bytes)
            fmt += f"{field.size}s" if is_string else f"{count}{base.fmt}"
            self.readers.append(
                FieldReader(
                    name,
                    index,
                    count,
                    offset,
                    base.size,
                    base.invalid_value,
                    4
                    if base.value_type is bytes
                    else 1
                    if is_string
                    else 2
                    if base.name == "byte"
                    else 3
                    if base.value_type is float
                    else 0,
                    plan,
                )
            )
            index += 1 if is_string else count
            offset += field.size
        self.unpacker = struct.Struct(fmt)
        self.sources = expansion_sources(
            self.profile_plan, {source.name for source in sources}
        )
        native_names = {reader.name for reader in self.readers}
        self.seeds = tuple(
            seed
            for seed in self.profile_plan.seeds
            if seed[0] in {reader.name for reader in self.readers if reader.kind != 4}
        )
        targets = {
            component.target
            for source in self.sources
            for expansion in (source.expansion, *(v.expansion for v in source.variants))
            if expansion is not None
            for component in expansion.components
        }
        self.preserve = (
            tuple(
                field.field_name
                for field in profile.fields.values()
                if field.field_name in native_names
                and field.field_name in targets
                and not field.array
            )
            if profile
            else ()
        )
        self.needs_raw = bool(sources or self.seeds)
        self.native_arrays = (
            tuple(
                field.field_name
                for field in profile.fields.values()
                if field.field_name in native_names
                and field.field_name in targets
                and field.array
            )
            if profile
            else ()
        )
        self.last_native: dict | None = None

    def read(self, data: Streamable, accumulators: Accumulators) -> dict[str, Any]:
        payload = data.read(self.unpacker.size)
        values = self.unpacker.unpack(payload)
        fields: dict[str, Any] = {}
        raw: dict[str, Any] = {} if self.needs_raw else fields
        for reader in self.readers:
            value = values[reader.index]
            if reader.kind == 1:
                value = decode_string(value)
            elif reader.kind == 4:
                pass
            elif reader.count > 1:
                items = values[reader.index : reader.index + reader.count]
                if reader.kind == 2:
                    value = (
                        None
                        if all(item == reader.invalid for item in items)
                        else list(items)
                    )
                elif reader.kind == 3:
                    value = [
                        None
                        if math.isnan(item)
                        and payload[
                            reader.offset + i * reader.size : reader.offset
                            + (i + 1) * reader.size
                        ]
                        == b"\xff" * reader.size
                        else item
                        for i, item in enumerate(items)
                    ]
                    if all(item is None for item in value):
                        value = None
                else:
                    value = [None if item == reader.invalid else item for item in items]
                    if all(item is None for item in value):
                        value = None
            elif reader.kind == 3:
                if (
                    math.isnan(value)
                    and payload[reader.offset : reader.offset + reader.size]
                    == b"\xff" * reader.size
                ):
                    value = None
            elif value == reader.invalid:
                value = None
            if self.needs_raw:
                raw[reader.name] = value
            if reader.plan is not None and (
                reader.plan.scale != 1 or reader.plan.offset != 0
            ):
                value = transform(value, reader.plan.scale, reader.plan.offset)
            fields[reader.name] = value
        if self.native_arrays:
            self.last_native = {
                name: fields[name].copy()
                if isinstance(fields[name], list)
                else fields[name]
                for name in self.native_arrays
            }
        if self.needs_raw:
            # Expansion appends to destination arrays; never alias the raw input.
            for field_name, field_value in fields.items():
                if isinstance(field_value, list):
                    fields[field_name] = field_value.copy()
            apply_components(
                raw,
                fields,
                self.seeds,
                self.sources,
                accumulators,
                self.preserve,
                scaled=self.options.apply_scale_and_offset,
                subfields=self.options.expand_subfields,
                components=self.options.expand_components,
            )
        return fields
