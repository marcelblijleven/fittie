import struct

from fittie.fitfile.crc import calculate_crc
from fittie.fitfile.utils.datastream import Streamable
from fittie.fitfile.utils.exceptions import DecodeException

DEFAULT_CRC = 0x0000


class Header:
    """
    File header which provides data about the FIT File

    Minimum size is 12 bytes, but a 14 byte header is preferred.

    Computing the CRC is optional and 0x0000 is a permissible CRC value
    """

    fmt: str = "<BBHI4s"
    length: int
    protocol_version: int
    profile_version: int
    data_size: int
    data_type: str
    crc: int

    def __init__(
        self,
        length: int,
        protocol_version: int,
        profile_version: int,
        data_size: int,
        data_type: str,
        crc: int,
        extra_header: bytes = b"",
    ) -> None:
        self.length = length
        self.protocol_version = protocol_version
        self.profile_version = profile_version
        self.data_size = data_size
        self.data_type = data_type
        self.crc = crc
        self.extra_header = extra_header

    def encode(self) -> bytes:
        """Encode the header into bytes"""
        values = (
            self.length,
            self.protocol_version,
            self.profile_version,
            self.data_size,
            self.data_type.encode("utf-8"),
        )

        encoded = struct.pack(self.fmt, *values)
        if self.length >= 14:
            encoded += self.extra_header + struct.pack("<H", self.crc)
        return encoded

    def __str__(self) -> str:
        return (
            f"Header:{self.length=}{self.protocol_version=}"
            f"{self.profile_version=}{self.data_size=}"
            f"{self.data_type=}{self.crc=}"
        ).replace("self.", " ")


def decode_header(data: Streamable, *, first_byte: bytes = b"") -> Header:
    """Read and validate a FIT header; header integers are always little endian."""
    start = data.tell() - len(first_byte)
    try:
        header_data = first_byte + data.read(12 - len(first_byte))
        length, protocol_version, profile_version, data_size, signature = struct.unpack(
            "<BBHI4s", header_data
        )
        if length != 12 and length < 14:
            raise DecodeException(detail="invalid FIT header size", position=start)
        if signature != b".FIT":
            raise DecodeException(detail="invalid FIT signature", position=start)
        if protocol_version >> 4 not in (1, 2):
            raise DecodeException(
                detail="unsupported FIT protocol version", position=start
            )
        crc = DEFAULT_CRC
        extra_header = b""
        if length >= 14:
            extra_header = data.read(length - 14)
            (crc,) = struct.unpack("<H", data.read(2))
            if (
                crc != 0
                and getattr(data, "should_calculate_crc", True)
                and crc != calculate_crc(header_data + extra_header)
            ):
                raise DecodeException(
                    detail="invalid crc checksum in file header", position=start
                )
    except (struct.error, EOFError) as exc:
        raise DecodeException(
            detail="could not decode header with provided data", position=data.tell()
        ) from exc
    return Header(
        length, protocol_version, profile_version, data_size, ".FIT", crc, extra_header
    )
