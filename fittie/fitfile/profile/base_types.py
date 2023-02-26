from __future__ import annotations

import struct
from typing import Optional

from fittie.utils.datastream import Streamable


class BaseType:
    """Representation of a Garmin FIT File Base Type"""

    number: int
    endian_ability: int
    name: str
    invalid_value: int
    size: int
    fmt: str
    value_type: type
    comment: str

    def __init__(
        self,
        number: int,
        endian_ability: int,
        name: str,
        invalid_value: int,
        size: int,
        fmt: str,
        value_type: type,
        comment: Optional[str] = None,
    ):
        self.number = number
        self.endian_ability = endian_ability
        self.name = name
        self.invalid_value = invalid_value
        self.size = size
        self.fmt = fmt
        self.value_type = value_type
        self.comment = comment if comment is not None else ""

    def __str__(self) -> str:
        return f"BaseType:{self.name=}{self.number=}".replace("self.", " ")

    def __repr__(self) -> str:
        return str(self)

    def get_value(
        self, endianness: str, data: Streamable
    ) -> Optional[BaseType.value_type]:
        # TODO: check for endian ability before creating fmt_string?
        fmt_string = f"{endianness}{self.fmt}"

        (value,) = struct.unpack(fmt_string, data.read(self.size))

        if value == self.invalid_value:
            return None

        return value


BASE_TYPES = {
    0x00: BaseType(
        number=0,
        endian_ability=0,
        name="enum",
        invalid_value=0xFF,
        size=1,
        fmt="B",
        value_type=int,
        comment="",
    ),
    0x01: BaseType(
        number=1,
        endian_ability=0,
        name="sint8",
        invalid_value=0x7F,
        size=1,
        fmt="b",
        value_type=int,
        comment="2’s complement format",
    ),
    0x02: BaseType(
        number=2,
        endian_ability=0,
        name="uint8",
        invalid_value=0xFF,
        size=1,
        fmt="B",
        value_type=int,
        comment="2’s complement format",
    ),
    0x83: BaseType(
        number=3,
        endian_ability=1,
        name="sint16",
        invalid_value=0x7FFF,
        size=2,
        fmt="h",
        value_type=int,
        comment="2’s complement format",
    ),
    0x84: BaseType(
        number=4,
        endian_ability=1,
        name="uint16",
        invalid_value=0xFFFF,
        size=2,
        fmt="H",
        value_type=int,
        comment="",
    ),
    0x85: BaseType(
        number=5,
        endian_ability=1,
        name="sint32",
        invalid_value=0x7FFFFFFF,
        size=4,
        fmt="i",
        value_type=int,
        comment="2’s complement format",
    ),
    0x86: BaseType(
        number=6,
        endian_ability=1,
        name="uint32",
        invalid_value=0xFFFFFFFF,
        size=4,
        fmt="I",
        value_type=int,
        comment="",
    ),
    0x07: BaseType(
        number=7,
        endian_ability=0,
        name="string",
        invalid_value=0x00,
        size=1,
        fmt="s",
        value_type=str,
        comment="Null terminated string encoded in UTF-8 format",
    ),
    0x88: BaseType(
        number=8,
        endian_ability=1,
        name="float32",
        invalid_value=0xFFFFFFFF,
        size=4,
        fmt="f",
        value_type=float,
        comment="",
    ),
    0x89: BaseType(
        number=9,
        endian_ability=1,
        name="float64",
        invalid_value=0xFFFFFFFFFFFFFFFF,
        size=8,
        fmt="d",
        value_type=float,
        comment="",
    ),
    0x0A: BaseType(
        number=10,
        endian_ability=0,
        name="uint8z",
        invalid_value=0x00,
        size=1,
        fmt="B",
        value_type=int,
        comment="",
    ),
    0x8B: BaseType(
        number=11,
        endian_ability=1,
        name="uint16z",
        invalid_value=0x0000,
        size=2,
        fmt="H",
        value_type=int,
        comment="",
    ),
    0x8C: BaseType(
        number=12,
        endian_ability=1,
        name="uint32z",
        invalid_value=0x00000000,
        size=4,
        fmt="I",
        value_type=int,
        comment="",
    ),
    0x0D: BaseType(
        number=13,
        endian_ability=1,
        name="byte",
        invalid_value=0xFF,
        size=1,
        fmt="B",
        value_type=int,
        comment="Array of bytes. Field is invalid if all bytes are invalid.",
    ),
    0x8E: BaseType(
        number=14,
        endian_ability=1,
        name="sint64",
        invalid_value=0x7FFFFFFFFFFFFFFF,
        size=8,
        fmt="q",
        value_type=int,
        comment="2’s complement format",
    ),
    0x8F: BaseType(
        number=15,
        endian_ability=1,
        name="uint64",
        invalid_value=0xFFFFFFFFFFFFFFFF,
        size=8,
        fmt="Q",
        value_type=int,
        comment="",
    ),
    0x90: BaseType(
        number=16,
        endian_ability=1,
        name="uint64z",
        invalid_value=0x0000000000000000,
        size=8,
        fmt="Q",
        value_type=int,
        comment="",
    ),
}
