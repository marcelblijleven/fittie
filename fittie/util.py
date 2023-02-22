from enum import StrEnum as _StrEnum


class Endianness(_StrEnum):
    """Helper enum for representing Big (>, MSB) and Little (<, LSB) Endianness"""

    BIG = ">"
    LITTLE = "<"

    def __repr__(self) -> str:
        return self.name
