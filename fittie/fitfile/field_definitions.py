from __future__ import annotations  # Added for type hints

import struct
from typing import Any, TypeVar

from fittie.fitfile.field_description import FieldDescription
from fittie.fitfile.strings import decode_string
from fittie.fitfile.utils.datastream import Streamable
from fittie.fitfile.utils.exceptions import DecodeException
from fittie.profile.base_types import BASE_TYPES, BaseType

T = TypeVar("T")


class DeveloperFieldDefinition:
    """
    Specifies Developer Data Fields which are used to map data within a DataMessage
    to the appropriate meta-data

    Byte 0 Field Number
    Byte 1 Size
    Byte 2 Developer Data Index
    """

    number: int
    size: int
    data_index: int

    def __init__(self, number: int, size: int, data_index: int):
        self.number = number
        self.size = size
        self.data_index = data_index

    def __str__(self) -> str:
        return (
            f"DeveloperFieldDefinition:{self.number=}{self.size=}{self.data_index=}"
        ).replace("self.", " ")

    def __repr__(self) -> str:
        return str(self)


class FieldDefinition:
    """
    Specifies which FIT fields are included in the upcoming data message

    Byte 0 Field Definition Number
    Byte 1 Size
    Byte 2 Base Type
    """

    number: int
    size: int
    base_type: BaseType

    def __init__(
        self, number: int, size: int, base_type: BaseType, wire_type: int | None = None
    ):
        self.number = number
        self.size = size
        self.base_type = base_type
        self.wire_type = (
            wire_type
            if wire_type is not None
            else next(
                (n for n, b in BASE_TYPES.items() if b is base_type), base_type.number
            )
        )

    def __str__(self) -> str:
        return f"FieldDefinition:{self.number=}{self.size=}{self.base_type=}".replace(
            "self.", " "
        )

    def __repr__(self) -> str:
        return str(self)


def decode_developer_field_definition(data: Streamable) -> DeveloperFieldDefinition:
    """
    Decode data into a DeveloperFieldDefinition
    """
    try:
        number, size, data_index = struct.unpack("3B", data.read(3))
    except struct.error as exc:
        raise DecodeException(
            detail="could not decode developer field definition with provided data",
            position=data.tell(),
        ) from exc

    if number == 255 or data_index == 255 or size == 0:
        raise DecodeException(
            detail="invalid developer field definition", position=data.tell()
        )

    return DeveloperFieldDefinition(
        number=number,
        size=size,
        data_index=data_index,
    )


def decode_field_definition(data: Streamable) -> FieldDefinition:
    """
    Decode data into a FieldDefinition

    If number equals 255 a DecodeException will be raised
    Unknown base types are retained as opaque byte fields, preserving stream
    alignment for future profiles.
    """
    try:
        number, size, base_type_number = struct.unpack("3B", data.read(3))
    except struct.error as exc:
        raise DecodeException(
            detail="could not decode field definition with provided data",
            position=data.tell(),
        ) from exc

    if number == 255:
        raise DecodeException(
            detail="invalid field definition number received",
            position=data.tell(),
        )

    base_type = BASE_TYPES.get(base_type_number)
    if base_type is None:
        base_type = BaseType(
            base_type_number & 0x1F, 0, f"unknown_{base_type_number}", 0, 1, "s", bytes
        )
    return FieldDefinition(
        number=number, size=size, base_type=base_type, wire_type=base_type_number
    )


def _retrieve_value(
    number_of_values: int,
    base_type: BaseType[T],
    endianness: str,
    data: Streamable,
) -> Any:
    if number_of_values < 1:
        raise DecodeException(detail="invalid field size", position=data.tell())
    if base_type.value_type is bytes:
        return data.read(number_of_values)
    if base_type.value_type is str:
        raw = data.read(number_of_values)
        return decode_string(raw)
    if number_of_values > 1 and base_type.name == "byte":
        raw_bytes = data.read(number_of_values)
        return None if all(value == 255 for value in raw_bytes) else list(raw_bytes)
    if number_of_values > 1:
        values = [
            base_type.get_value(endianness, data) for _ in range(number_of_values)
        ]
        return None if all(value is None for value in values) else values
    return base_type.get_value(endianness, data)


def read_field(
    field_definition: FieldDefinition,
    endianness: str,
    data: Streamable,
) -> Any:
    """
    Read field by field definition
    """
    base_type = field_definition.base_type
    if base_type is None:
        return data.read(field_definition.size)
    if field_definition.size % base_type.size:
        raise DecodeException(
            detail="field size is not a multiple of its base type", position=data.tell()
        )
    number_of_values = field_definition.size // base_type.size

    return _retrieve_value(number_of_values, base_type, endianness, data)


def read_developer_field(
    field_description: FieldDescription,
    field_definition: DeveloperFieldDefinition,
    endianness: str,
    data: Streamable,
) -> Any:
    """
    Read developer data field by field definition and field description
    """

    base_type = field_description.base_type
    if base_type is None:
        return data.read(field_definition.size)
    if field_definition.size % base_type.size:
        raise DecodeException(
            detail="field size is not a multiple of its base type", position=data.tell()
        )
    number_of_values = field_definition.size // base_type.size

    return _retrieve_value(number_of_values, base_type, endianness, data)
