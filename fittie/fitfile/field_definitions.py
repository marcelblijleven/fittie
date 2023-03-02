from __future__ import annotations  # Added for type hints

import struct
from typing import Any

from fittie.utils.datastream import Streamable
from fittie.utils.exceptions import DecodeException
from fittie.fitfile.field_description import FieldDescription
from fittie.fitfile.profile.base_types import BaseType, BASE_TYPES


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

    def __init__(self, number: int, size: int, base_type: BaseType):
        self.number = number
        self.size = size
        self.base_type = base_type

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

    return DeveloperFieldDefinition(
        number=number,
        size=size,
        data_index=data_index,
    )


def decode_field_definition(data: Streamable) -> FieldDefinition:
    """
    Decode data into a FieldDefinition

    If number equals 255 a DecodeException will be raised
    If no base type can be found for the base type number, a DecodeException will be
    raised
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

    if not (base_type := BASE_TYPES.get(base_type_number)):
        raise DecodeException(
            detail=f"invalid base type number received: {base_type_number=}",
            position=data.tell(),
        )

    return FieldDefinition(number=number, size=size, base_type=base_type)


def _retrieve_value(
    number_of_values: int,
    base_type: BaseType,
    endianness: str,
    data: Streamable,
) -> Any:
    if number_of_values > 1:
        value = []

        for n in range(number_of_values):
            # (n_value,) = struct.unpack(
            #     f"{endianness}{base_type.size}{base_type.fmt}",
            #     data.read(base_type.size)
            # )
            n_value = base_type.get_value(endianness, data)

            # Null terminated string check
            if base_type.value_type == str and n_value == b"\x00":
                continue  # Just continue, there can be more than one \x00

            if n_value == base_type.invalid_value:
                value.append(None)
            else:
                value.append(n_value)

        if base_type.value_type == str:
            value = b"".join(value).decode("utf-8")
    else:
        value = base_type.get_value(endianness, data)

    return value


def read_field(
    field_definition: FieldDefinition,
    endianness: str,
    data: Streamable,
) -> Any:
    """
    Read field by field definition
    """
    base_type = field_definition.base_type
    number_of_values = int(field_definition.size / base_type.size)

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
    number_of_values = int(field_definition.size / base_type.size)

    return _retrieve_value(number_of_values, base_type, endianness, data)
