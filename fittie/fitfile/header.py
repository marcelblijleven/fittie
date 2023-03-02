import struct
from io import BytesIO

from fittie.utils.datastream import Streamable
from fittie.utils.exceptions import DecodeException
from fittie.fitfile.crc import calculate_crc

DEFAULT_CRC = 0x0000


class Header:
    """
    File header which provides data about the FIT File

    Minimum size is 12 bytes, but a 14 byte header is preferred.

    Computing the CRC is optional and 0x0000 is a permissible CRC value
    """

    fmt: str = "BBHI4s"
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
    ) -> None:
        self.length = length
        self.protocol_version = protocol_version
        self.profile_version = profile_version
        self.data_size = data_size
        self.data_type = data_type
        self.crc = crc

    def encode(self) -> bytes:
        """Encode the header into bytes"""
        values = (
            self.length,
            self.protocol_version,
            self.profile_version,
            self.data_size,
            self.data_type.encode("utf-8"),
        )

        if self.length == 14:
            self.fmt += "H"  # add additional 2 bytes for CRC
            values += (self.crc,)

        return struct.pack(self.fmt, *values)

    def __str__(self) -> str:
        return (
            f"Header:{self.length=}{self.protocol_version=}"
            f"{self.profile_version=}{self.data_size=}"
            f"{self.data_type=}{self.crc=}"
        ).replace("self.", " ")


def decode_header(data: Streamable) -> Header:
    """
    Reads a FIT file header from the provided data
    """
    try:
        # Read first 12 bytes to determine header size
        header_data = data.read(12)
        header_reader = BytesIO(header_data)

        (length,) = struct.unpack("B", header_reader.read(1))
        (protocol_version,) = struct.unpack("B", header_reader.read(1))
        (profile_version,) = struct.unpack("H", header_reader.read(2))
        (data_size,) = struct.unpack("I", header_reader.read(4))
        data_type = b"".join(struct.unpack("4s", header_reader.read(4))).decode("utf-8")

        if length == 14:
            (crc,) = struct.unpack("H", data.read(2))
            calculated_crc = calculate_crc(header_data)

            if crc != calculated_crc:
                raise DecodeException(
                    detail="invalid crc checksum in file header", position=0
                )
        else:
            crc = DEFAULT_CRC
    except struct.error as exc:
        raise DecodeException(
            detail="could not decode header with provided data",
            position=data.tell(),
        ) from exc

    header = Header(
        length=length,
        protocol_version=protocol_version,
        profile_version=profile_version,
        data_size=data_size,
        data_type=data_type,
        crc=crc,
    )

    return header
