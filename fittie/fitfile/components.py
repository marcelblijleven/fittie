"""Compile profile metadata once; keep all accumulator state local to a FIT member."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from graphlib import TopologicalSorter
from math import lcm
from typing import Any

from fittie.fitfile.strings import decode_string
from fittie.profile.base_types import BASE_TYPES, BaseType
from fittie.profile.fit_types import FIT_TYPES
from fittie.profile.message_profile import FieldProfile, MessageProfile, SubField
from fittie.profile.util import get_message_profile

# Scale and offset identify the counter's units. Bit width may change across definitions.
AccumulatorKey = tuple[int, str, float, float]
Accumulators = dict[AccumulatorKey, int]
Seed = tuple[str, int, int, int, AccumulatorKey]


def _conversion(
    source_scale: float, source_offset: float, target_scale: float, target_offset: float
) -> tuple[int, int, int]:
    """Compile raw-unit conversion as integers to avoid float truncation/roundoff."""
    multiplier = Fraction(str(target_scale)) / Fraction(str(source_scale))
    offset = (Fraction(str(target_offset)) - Fraction(str(source_offset))) * Fraction(
        str(target_scale)
    )
    denominator = lcm(multiplier.denominator, offset.denominator)
    return (
        multiplier.numerator * (denominator // multiplier.denominator),
        offset.numerator * (denominator // offset.denominator),
        denominator,
    )


def _raw_value(value: int, multiplier: int, offset: int, denominator: int) -> int:
    numerator = value * multiplier + offset
    return numerator // denominator if numerator >= 0 else -(-numerator // denominator)


def _items(value: Any, count: int, default: Any) -> list:
    if value is None:
        return [default] * count
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, list):
        values = value
    else:
        values = [value]
    if len(values) == 1:
        return values * count
    if len(values) != count:
        raise ValueError("component metadata has inconsistent lengths")
    return values


def _base_type(field_type: str) -> BaseType:
    name = (
        FIT_TYPES[field_type].base_type
        if field_type in FIT_TYPES
        else "enum"
        if field_type == "bool"
        else field_type
    )
    return next(base for base in BASE_TYPES.values() if base.name == name)


def scalar_scale(profile: FieldProfile | SubField) -> float:
    # A multi-component field's scales describe its components, not the container.
    return float(profile.scale) if isinstance(profile.scale, (int, float)) else 1


@dataclass(frozen=True, slots=True)
class Component:
    target: str
    shift: int
    bits: int
    mask: int
    scale: float
    offset: float
    target_scale: float
    target_offset: float
    conversion: tuple[int, int, int]
    invalid: int
    signed: bool
    byte_array: bool
    string: bool
    key: AccumulatorKey | None


@dataclass(frozen=True, slots=True)
class Expansion:
    name: str
    base_bits: int
    invalid: int
    components: tuple[Component, ...]
    alias: bool


@dataclass(frozen=True, slots=True)
class Variant:
    name: str
    refs: tuple[tuple[str, int | str], ...]
    scale: float
    offset: float
    expansion: Expansion | None


@dataclass(frozen=True, slots=True)
class FieldPlan:
    name: str
    scale: float
    offset: float
    expansion: Expansion | None
    variants: tuple[Variant, ...]
    expansions: tuple[Expansion, ...] = ()


@dataclass(frozen=True, slots=True)
class ProfilePlan:
    fields: dict[str, FieldPlan]
    order: dict[str, int]
    # Native full-width values seed the same counters as compressed components.
    seeds: tuple[Seed, ...]


def _expansion(
    number: int, profile: FieldProfile | SubField, message: MessageProfile
) -> Expansion | None:
    if not profile.components:
        return None
    names = (
        [profile.components]
        if isinstance(profile.components, str)
        else profile.components
    )
    count = len(names)
    bits = _items(profile.bits, count, 0)
    scales = _items(profile.scale, count, 1)
    offsets = _items(profile.offset, count, 0)
    accumulated = _items(profile.accumulate, count, 0)
    targets = {field.field_name: field for field in message.fields.values()}
    result = []
    shift = 0
    for name, width, scale, offset, accumulate in zip(
        names, bits, scales, offsets, accumulated
    ):
        width, scale, offset = int(width), float(scale), float(offset)
        if not 1 <= width <= 64 or scale == 0:
            raise ValueError(f"invalid component metadata for {profile.field_name}")
        target = targets[name]
        base = _base_type(target.field_type)
        enum = base.name in ("enum", "string")
        if enum:
            scale, offset = 1, 0
        result.append(
            Component(
                name,
                shift,
                width,
                (1 << width) - 1,
                scale,
                offset,
                scalar_scale(target),
                target.offset or 0,
                _conversion(scale, offset, scalar_scale(target), target.offset or 0),
                base.invalid_value,
                base.name.startswith("sint"),
                base.name == "byte" and bool(target.array),
                base.name == "string",
                (number, name, scale, offset) if int(accumulate) else None,
            )
        )
        shift += width
    base = _base_type(profile.field_type)
    return Expansion(
        profile.field_name,
        base.size * 8,
        base.invalid_value,
        tuple(result),
        len(result) == 1
        and result[0].bits == base.size * 8
        and result[0].conversion == (1, 0, 1)
        and result[0].key is None
        and result[0].scale == scalar_scale(profile)
        and result[0].offset == (profile.offset or 0)
        and not result[0].signed
        and not result[0].string,
    )


@cache
def get_profile_plan(number: int) -> ProfilePlan:
    message = get_message_profile(number)
    if message is None:
        return ProfilePlan({}, {}, ())
    plans = {}
    seeds = {}
    for field in message.fields.values():
        expansion = _expansion(number, field, message)
        variants = tuple(
            Variant(
                sub.field_name,
                tuple(
                    (str(ref["field_name"]), ref["value_number"])
                    for ref in sub.refs
                    if ref is not None
                ),
                scalar_scale(sub),
                sub.offset or 0,
                _expansion(number, sub, message),
            )
            for sub in field.subfields or ()
        )
        plans[field.field_name] = FieldPlan(
            field.field_name,
            scalar_scale(field),
            field.offset or 0,
            expansion,
            variants,
            (expansion,) if expansion is not None else (),
        )
        for item in (expansion, *(variant.expansion for variant in variants)):
            if item is not None:
                for component in item.components:
                    if component.key is not None:
                        seeds[component.key] = (
                            component.target,
                            *_conversion(
                                component.target_scale,
                                component.target_offset,
                                component.scale,
                                component.offset,
                            ),
                            component.key,
                        )

    # Component and reference dependencies are evaluated once, not per record.
    dependencies: dict[str, set[str]] = {name: set() for name in plans}
    for name, plan in plans.items():
        for variant in plan.variants:
            dependencies[name].update(ref for ref, _ in variant.refs)
        for expansion in (plan.expansion, *(v.expansion for v in plan.variants)):
            if expansion is not None:
                for component in expansion.components:
                    dependencies[component.target].add(name)
    order = {
        name: index
        for index, name in enumerate(TopologicalSorter(dependencies).static_order())
    }
    return ProfilePlan(plans, order, tuple(seeds.values()))


def expansion_sources(plan: ProfilePlan, names: set[str]) -> tuple[FieldPlan, ...]:
    """Include nested destinations; resolve references after their producers."""
    pending = list(names)
    visited: set[str] = set()
    sources = []
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        field = plan.fields[name]
        if field.expansion is not None or field.variants:
            sources.append(field)
        for expansion in (field.expansion, *(v.expansion for v in field.variants)):
            if expansion is not None:
                pending.extend(component.target for component in expansion.components)
    sources.sort(key=lambda source: plan.order[source.name])
    return tuple(sources)


def transform(value: Any, scale: float, offset: float) -> Any:
    if value is None or (scale == 1 and offset == 0):
        return value
    if isinstance(value, list):
        return [None if item is None else item / scale - offset for item in value]
    return value / scale - offset


def _append(fields: dict[str, Any], name: str, value: Any, first: bool) -> None:
    """Retain native values followed by expanded values, in wire/component order."""
    current = fields.get(name)
    if current is None and first:
        fields[name] = value
    elif isinstance(current, list):
        current.append(value)
    else:
        fields[name] = [current, value]


def apply_components(
    raw: dict[str, Any],
    fields: dict[str, Any],
    seeds: tuple[Seed, ...],
    sources: tuple[FieldPlan, ...],
    accumulators: Accumulators,
    preserve: tuple[str, ...] = (),
    *,
    scaled: bool = True,
    subfields: bool = True,
    components: bool = True,
) -> None:
    for name, multiplier, offset, denominator, key in seeds if components else ():
        value = raw.get(name)
        if value is None:
            continue
        if isinstance(value, list):
            value = next((item for item in reversed(value) if item is not None), None)
            if value is None:
                continue
        accumulators[key] = _raw_value(value, multiplier, offset, denominator)

    preserved = {name for name in preserve if raw.get(name) is not None}
    expanded: dict[str, bool] = {}
    strings: dict[str, bytearray] = {}
    for source in sources:
        value = raw.get(source.name)
        if value is None:
            continue
        source_value = value
        expansions = source.expansions
        for variant in source.variants if subfields else ():
            if any(raw.get(name) == expected for name, expected in variant.refs):
                fields[variant.name] = (
                    transform(value, variant.scale, variant.offset) if scaled else value
                )
                if variant.expansion is not None:
                    expansions += (variant.expansion,)
        if not components:
            continue
        for expansion in expansions:
            if expansion is None:
                continue
            value = source_value
            if expansion.alias and isinstance(value, int):
                component = expansion.components[0]
                if 0 <= value <= component.mask:
                    if component.target not in preserved:
                        physical_value = (
                            None
                            if value == component.invalid
                            else fields[expansion.name]
                        )
                        first = component.target not in expanded
                        _append(fields, component.target, physical_value, first)
                        _append(
                            raw,
                            component.target,
                            None if physical_value is None else value,
                            first,
                        )
                        expanded[component.target] = component.byte_array
                    continue
            # Pack logical base-type elements LSB first; the wire's endianness has
            # already been resolved by the binary reader. No per-bit Python loop.
            if isinstance(value, (str, bytes)):
                packed_bytes = (
                    value.encode("utf-8") if isinstance(value, str) else value
                )
                packed = int.from_bytes(packed_bytes, "little")
                available = len(packed_bytes) * 8
            elif isinstance(value, list):
                packed = 0
                mask = (1 << expansion.base_bits) - 1
                for index, item in enumerate(value):
                    packed |= (
                        (expansion.invalid if item is None else int(item)) & mask
                    ) << (index * expansion.base_bits)
                available = len(value) * expansion.base_bits
            else:
                packed = int(value)
                available = expansion.base_bits
            for component in expansion.components:
                if component.shift + component.bits > available:
                    break
                if component.target in preserved:
                    continue
                value_bits = (packed >> component.shift) & component.mask
                if component.string:
                    strings.setdefault(component.target, bytearray()).extend(
                        value_bits.to_bytes((component.bits + 7) // 8, "little")
                    )
                    fields[component.target] = decode_string(
                        bytes(strings[component.target])
                    )
                    raw[component.target] = fields[component.target]
                    continue
                if component.signed and value_bits & (1 << (component.bits - 1)):
                    value_bits -= 1 << component.bits
                if component.key is not None:
                    previous = accumulators.get(component.key, 0)
                    value_bits = previous + ((value_bits - previous) & component.mask)
                    accumulators[component.key] = value_bits
                physical = (
                    value_bits
                    if component.scale == 1 and component.offset == 0
                    else value_bits / component.scale - component.offset
                )
                target_raw = _raw_value(value_bits, *component.conversion)
                physical_value = (
                    None
                    if target_raw == component.invalid and not component.byte_array
                    else physical
                    if scaled
                    else target_raw
                )
                first = component.target not in expanded
                _append(fields, component.target, physical_value, first)
                _append(
                    raw,
                    component.target,
                    None if physical_value is None else target_raw,
                    first,
                )
                expanded[component.target] = component.byte_array
    for name, byte_array in expanded.items():
        result = fields[name]
        if isinstance(result, list) and all(item is None for item in result):
            fields[name] = None
        elif byte_array:
            values = result if isinstance(result, list) else [result]
            if all(item == 255 for item in values):
                fields[name] = None
