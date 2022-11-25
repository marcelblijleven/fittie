from io import BytesIO

from fittie.fitfile.header import FitFileHeader


def test_fitfileheader_from_data():
    data = BytesIO(b"\x0e \xf1\x07pf\x00\x00.FIT\xef\x91")
    header = FitFileHeader.from_data(data)

    assert header.length == 14
    assert header.profile_version == 2033
    assert header.protocol_version == 32
    assert header.data_size == 26224
    assert header.data_type == ".FIT"
    assert header.crc == 37359


def test_fitfileheader_decode():
    assert FitFileHeader.from_data == FitFileHeader.decode


def test_fitfileheader_encode():
    header = FitFileHeader(
        length=14,
        profile_version=2033,
        protocol_version=32,
        data_size=26224,
        data_type=".FIT",
        crc=37359,
    )

    assert header.encode() == b"\x0e \xf1\x07pf\x00\x00.FIT\xef\x91"
