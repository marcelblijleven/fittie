from io import BytesIO
from typing import BinaryIO

import pytest

from fittie.fitfile.header import Header, decode_header


@pytest.fixture
def header_bytes() -> bytes:
    return b"\x0e \xf1\x07pf\x00\x00.FIT\xef\x91"


@pytest.fixture
def header_data(header_bytes) -> BinaryIO:
    return BytesIO(header_bytes)


def test_decode_header(header_data) -> None:
    header = decode_header(header_data)

    assert header.length == 14
    assert header.profile_version == 2033
    assert header.protocol_version == 32
    assert header.data_size == 26224
    assert header.data_type == ".FIT"
    assert header.crc == 37359


def test_header_encode(header_bytes) -> None:
    header = Header(
        length=14,
        profile_version=2033,
        protocol_version=32,
        data_size=26224,
        data_type=".FIT",
        crc=37359,
    )

    assert header.encode() == header_bytes
