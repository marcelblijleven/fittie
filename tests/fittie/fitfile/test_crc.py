import pytest

from fittie.fitfile.crc import apply_crc, calculate_crc


def test_calculate_crc():
    assert calculate_crc(b"\x0e D\x08-\x86\x00\x00.FIT") == 3484


@pytest.mark.parametrize(
    "crc,value,expected",
    [
        (0, 14, 50305),
        (50305, 32, 47109),
        (47109, 68, 12408),
        (12408, 8, 58417),
    ],
)
def test_apply_crc(crc, value, expected):
    assert apply_crc(crc, value) == expected


def test_byte_table_matches_independent_bitwise_crc():
    for initial in (0, 1, 0xFF, 0x100, 0x1234, 0xFFFF):
        for byte in range(256):
            crc = initial ^ byte
            for _ in range(8):
                crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
            assert apply_crc(initial, byte) == crc


def test_incremental_crc_matches_whole_buffer():
    data = bytes(range(256))
    initial = calculate_crc(data[:100])
    assert calculate_crc(data[100:], initial) == calculate_crc(data)
