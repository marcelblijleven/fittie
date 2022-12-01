from io import BytesIO
from uuid import UUID

from fittie.fitfile.utils import rollover_timestamp, uuid_to_bytes, bytes_to_uuid, \
    get_length_of_binaryio


def test_rollover_timestamp():
    """
    Test data from FIT file documentation
    """
    initial_timestamp = 0x0000003B

    assert (
        resultant_timestamp := rollover_timestamp(initial_timestamp, 0b11101)
    ) == 0x3D

    assert (
        resultant_timestamp := rollover_timestamp(resultant_timestamp, 0b00010)
    ) == 0x42

    assert (
        resultant_timestamp := rollover_timestamp(resultant_timestamp, 0b00101)
    ) == 0x45

    assert rollover_timestamp(resultant_timestamp, 0b00001) == 0x61


def test_uuid_to_bytes():
    uuid = UUID("728d3309-139b-4a6d-b30e-f50cf0794c12")
    assert uuid_to_bytes(uuid) == b"mJ\x9b\x13\t3\x8dr\x12Ly\xf0\x0c\xf5\x0e\xb3"


def test_bytes_to_uuid():
    uuid = UUID("728d3309-139b-4a6d-b30e-f50cf0794c12")
    assert bytes_to_uuid(b"mJ\x9b\x13\t3\x8dr\x12Ly\xf0\x0c\xf5\x0e\xb3") == uuid


def test_get_length_of_binaryio():
    with open('data/sample_file.txt', 'rb') as f:
        assert get_length_of_binaryio(f) == 42

    assert get_length_of_binaryio(
        BytesIO(b'this is for testing binaryio (file) utils!')
    ) == 42
