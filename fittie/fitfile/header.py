from __future__ import annotations
from typing import BinaryIO

import struct

from fittie.fitfile.utils import get_length_of_binaryio


class FitFileHeader:
    """
    File header which provides data about the FIT file

    Minimum size is 12 bytes, but a 14 bytes header is preferred.

    Computing the CRC is optional and 0x0000 is a permissible CRC value
    """

    def __init__(
        self,
        length: int,
        protocol_version: int,
        profile_version: int,
        data_size: int,
        data_type: str,
        crc: int,
    ):
        self.length = length
        self.protocol_version = protocol_version
        self.profile_version = profile_version
        self.data_size = data_size
        self.data_type = data_type
        self.crc = crc

    @classmethod
    def from_data(cls, data: BinaryIO) -> FitFileHeader:
        """
        Takes a binary io object to read up to 14 bytes to determine the
        FitFileHeader
        """
        (length,) = struct.unpack("B", data.read(1))
        (protocol_version,) = struct.unpack("B", data.read(1))
        (profile_version,) = struct.unpack("H", data.read(2))
        (data_size,) = struct.unpack("I", data.read(4))
        data_type = b"".join(struct.unpack("4s", data.read(4))).decode("utf-8")

        if length == 14:
            (crc,) = struct.unpack("H", data.read(2))
        else:
            crc = 0x0000

        header = cls(length, protocol_version, profile_version, data_size, data_type, crc)

        if not header.is_valid(data):
            raise ValueError('provided data is not a valid FIT file')

        return header

    # Alias for from_data
    decode = from_data

    def encode(self) -> bytes:
        fmt = "BBHI4s"
        values = (
            self.length,
            self.protocol_version,
            self.profile_version,
            self.data_size,
            self.data_type.encode("utf8"),
        )

        if self.length == 14:
            fmt += "H"  # add additional 2 bytes for CRC
            values += (self.crc,)

        return struct.pack(fmt, *values)

    def is_valid(self, data: BinaryIO) -> bool:
        """
        Checks whether the FIT file is valid by checking the header length and
        the total size of incoming data

        - Header length should be 12 or 14
        - The length of the incoming data should be equal to the length attribute +
          data_size attribute + two for the crc value
        """

        if self.length != 12 and self.length != 14:
            return False

        if get_length_of_binaryio(data) != self.length + self.data_size + 2:
            return False

        return True

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            f"FitFileHeader,"
            f"protocol_version:{self.protocol_version},"
            f"profile_version:{self.profile_version}"
        )
