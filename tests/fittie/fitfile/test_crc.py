import pytest

from fittie.fitfile.crc import calculate_crc, apply_crc


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
