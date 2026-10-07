import os.path
from pathlib import Path
from typing import Any, BinaryIO, Protocol

from fittie.fitfile.crc import calculate_crc


class Streamable(Protocol):
    def read(self, size: int = 1) -> bytes: ...

    def tell(self) -> int: ...

    def close(self) -> None: ...


class DataStream:
    """
    A thin wrapper around a BinaryIO

    It allows a path, file content or a BinaryIO/Streamable to be provided as
    initial value.

    """

    _data: BinaryIO
    _path: str | Path | None
    _calculated_crc: int

    should_calculate_crc: bool

    def __init__(self, value: Any):
        self.should_calculate_crc = True
        self._calculated_crc = 0
        self.limit: int | None = None
        self._path = None
        self._position = 0

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

        if self._path is None:
            try:
                self._position = self._data.tell()
            except (AttributeError, OSError):
                self._position = 0

    @property
    def calculated_crc(self) -> int:
        """Returns the calculated crc, or 0 if crc calculation is disabled"""
        return self._calculated_crc

    def reset_crc(self) -> None:
        """Resets the calculated crc back to 0"""
        self._calculated_crc = 0

    def read(self, size: int = 1, *, allow_eof: bool = False) -> bytes:
        """
        Reads the provided number of bytes from the wrapped BinaryIO data

        If a crc should be calculated, the internal crc property will be calculated
        for each byte that was read.
        """
        if self.limit is not None and self._position + size > self.limit:
            raise EOFError("record extends beyond the FIT data section")
        value = self._data.read(size)
        received = len(value)
        if received != size:
            if allow_eof and not value:
                return value
            chunks = [value]
            while received < size and value:
                value = self._data.read(size - received)
                received += len(value)
                chunks.append(value)
            value = b"".join(chunks)
            if received != size:
                self._position += received
                raise EOFError("truncated FIT data")
        self._position += received
        if self.should_calculate_crc:
            self._calculated_crc = calculate_crc(value, self._calculated_crc)
        return value

    def tell(self) -> int:
        """Returns the current stream position"""
        return self._position

    def __enter__(self):
        if self._path is None:
            return self

        self._data = open(self._path, "rb")
        self._position = 0
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._path is not None:
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
            raise OSError(f"expected file to be opened with mode 'rb', got '{mode}'")

        return True

    @staticmethod
    def is_path(value: str | Path) -> bool:
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
        return hasattr(value, "read")
