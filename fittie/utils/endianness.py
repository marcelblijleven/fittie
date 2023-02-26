try:
    from enum import StrEnum as _StrEnum
except ImportError:
    from enum import Enum as _Enum

    class _StrEnum(str, _Enum):
        def __str__(self) -> str:
            return self.value


class Endianness(_StrEnum):
    """Helper enum for representing Big (>, MSB) and Little (<, LSB) Endianness"""

    BIG = ">"
    LITTLE = "<"

    def __repr__(self) -> str:
        return self.name
