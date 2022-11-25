import struct

from uuid import UUID


def check_crc() -> bool:
    """Checks the CRC in the header"""
    ...


def compute_crc() -> int:
    """Generates a CRC to include in the header"""
    ...


def rollover_timestamp(previous_timestamp: int, offset: int) -> int:
    """
    Apply the compressed timestamp offset to the previous timestamp

    The offset is a 5-bit offset which rolls over every 32 seconds
    (0b11111 == 31). This means that consecutive compressed timestamps may
    never be more than 32 seconds apart

    The actual timestamp is calculated by concatenating the most significant 27 bits
    of the previous timestamp value and the 5 bit value of the offset field
    """
    max_length = 0b1111  # 0x0000001F

    if offset >= previous_timestamp & max_length:
        # Offset value is greater than least significant 5 bits of previous timestamp
        timestamp = (previous_timestamp & 0xFFFFFFE0) + offset
    else:
        # Offset is less than least significant 5 bits of previous timestamp
        timestamp = (previous_timestamp & 0xFFFFFFE0) + offset + 0x20

    return timestamp


def uuid_to_bytes(uuid: UUID, endianness: str = '<') -> bytes:
    """Convert a 128 bit UUID to bytes"""
    # TODO: check if uuid.bytes works too

    fmt = f'{endianness}QQ'
    # Split the 128 bit UUID into two parts with bit shifting
    max_value = 0xFFFFFFFFFFFFFFFF  # max value for a int64
    return struct.pack(fmt, (uuid.int >> 64) & max_value, uuid.int & max_value)


def bytes_to_uuid(data: bytes, endianness: str = '<') -> UUID:
    """Convert bytes to a UUID"""
    # TODO: check if UUID(bytes=data) works too
    fmt = f'{endianness}QQ'
    part_a, part_b = struct.unpack(fmt, data)
    uuid_int = (part_a << 64) | part_b

    return UUID(int=uuid_int)
