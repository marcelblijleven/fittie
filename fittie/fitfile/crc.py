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


def apply_crc(crc: int, value: int) -> int:
    """
    Applies the crc computation on the provided value and returns it
    """
    # Compute checksum of lower four bits of byte
    tmp = TABLE[crc & 0xF]
    crc = (crc >> 4) & 0x0FFF
    crc = crc ^ tmp ^ TABLE[value & 0xF]

    # Compute checksum of upper four bits of byte
    tmp = TABLE[crc & 0xF]
    crc = (crc >> 4) & 0x0FFF
    crc = crc ^ tmp ^ TABLE[(value >> 4) & 0xF]

    return crc


def calculate_crc(data: bytes) -> int:
    """
    Calculates crc checksum for the entire provided data

    Compute method from https://developer.garmin.com/fit/protocol/
    """

    crc = 0

    for byte in data:
        crc = apply_crc(crc, byte)

    return crc
