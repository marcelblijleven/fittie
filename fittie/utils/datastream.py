import os.path
from pathlib import Path
from typing import Protocol, Optional, BinaryIO, Any, Union

from fittie.fitfile.crc import apply_crc


class Streamable(Protocol):
    def read(self, size: Optional[int] = 1) -> bytes:
        ...

    def tell(self) -> int:
        ...

    def close(self) -> None:
        ...


class DataStream:
    """
    A thin wrapper around a BinaryIO

    It allows a path, file content or a BinaryIO/Streamable to be provided as
    initial value.

    TODO: include CRC check
    """

    _data: BinaryIO
    _path: Optional[Union[str, Path]]
    _calculated_crc: int

    should_calculate_crc: bool

    def __init__(self, value: Any):
        self.should_calculate_crc = True
        self._calculated_crc = 0

        if DataStream.is_file(value):
            self._data = value
        elif DataStream.is_path(value):
            self._path = value
        elif DataStream.is_streamable(value):
            self._data = value
        else:
            raise ValueError(
                f"unsupported value received as stream input: {type(value)}"
            )

    @property
    def calculated_crc(self) -> int:
        """Returns the calculated crc, or 0 if crc calculation is disabled"""
        return self._calculated_crc

    def reset_crc(self) -> None:
        """Resets the calculated crc back to 0"""
        self._calculated_crc = 0

    def read(self, size: Optional[int] = 1) -> bytes:
        """
        Reads the provided number of bits from the wrapped BinaryIO data

        If a crc should be calculated, the internal crc property will be calculated
        for each byte that was read.
        """
        if not self.should_calculate_crc:
            return self._data.read(size)

        value = self._data.read(size)

        for idx in range(0, size):
            self._calculated_crc = apply_crc(self._calculated_crc, value[idx])
        return value

    def tell(self) -> int:
        """Returns the current stream position"""
        return self._data.tell()

    def __enter__(self):
        if not hasattr(self, "_path"):
            return self

        self._data = open(self._path, "rb")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._data.close()

    @staticmethod
    def is_file(value) -> bool:
        """
        Checks if the provided value is a BufferedReader (file) with the correct mode.

        Raises IOError if file is not opened in rb mode
        """

        if not hasattr(value, "mode"):
            return False

        if (mode := getattr(value, "mode")) != "rb":
            raise IOError(f"expected file to be opened with mode 'rb', got '{mode}'")

        return True

    @staticmethod
    def is_path(value: Union[str, Path]) -> bool:
        """
        Check if the provided value is either a path string or Path, and checks if the
        file exists.

        Raises FileNotFoundError if path doesn't exist.
        """
        if not isinstance(value, str) and not isinstance(value, Path):
            return False

        if not os.path.exists(value):
            raise FileNotFoundError(f"file {value} does not exist")

        return True

    @staticmethod
    def is_streamable(value: Streamable) -> bool:
        """Check if the provided value has a read and tell method"""
        return hasattr(value, "read") and hasattr(value, "tell")
