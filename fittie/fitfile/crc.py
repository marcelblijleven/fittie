TABLE = (
    0x0000,
    0xCC01,
    0xD801,
    0x1400,
    0xF001,
    0x3C00,
    0x2800,
    0xE401,
    0xA001,
    0x6C00,
    0x7800,
    0xB401,
    0x5000,
    0x9C01,
    0x8801,
    0x4400,
)


def _table_entry(value: int) -> int:
    for _ in range(8):
        value = (value >> 1) ^ (0xA001 if value & 1 else 0)
    return value


BYTE_TABLE = tuple(_table_entry(value) for value in range(256))


def apply_crc(crc: int, value: int) -> int:
    """Update FIT's CRC-16 using a precomputed byte table."""
    return (crc >> 8) ^ BYTE_TABLE[(crc ^ value) & 0xFF]


def calculate_crc(data: bytes, initial_crc: int = 0) -> int:
    """
    Calculates crc checksum for the entire provided data

    Compute method from https://developer.garmin.com/fit/protocol/
    """

    crc = initial_crc
    table = BYTE_TABLE
    for byte in data:
        crc = (crc >> 8) ^ table[(crc ^ byte) & 0xFF]

    return crc
