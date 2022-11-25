from __future__ import annotations
from typing import BinaryIO

import struct


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

        return cls(length, protocol_version, profile_version, data_size, data_type, crc)

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

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            f"FitFileHeader,"
            f"protocol_version:{self.protocol_version},"
            f"profile_version:{self.profile_version}"
        )
