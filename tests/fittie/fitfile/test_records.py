from io import BytesIO
from fittie.fitfile.records import read_record_header


def test_record_header() -> None:
    # Definition message
    data = BytesIO(initial_bytes=0b01000000.to_bytes(length=1, byteorder="big"))
    header = read_record_header(data)
    assert header.is_definition_message
    assert header.local_message_type == 0
    assert not header.is_developer_data

    # Data message
    data = BytesIO(initial_bytes=0b00000000.to_bytes(length=1, byteorder="big"))
    header = read_record_header(data)
    assert not header.is_definition_message
    assert header.local_message_type == 0
    assert not header.is_developer_data

    # Definition message with developer data
    data = BytesIO(initial_bytes=0b01100001.to_bytes(length=1, byteorder="big"))
    header = read_record_header(data)
    assert header.is_definition_message
    assert header.local_message_type == 1
    assert header.is_developer_data

    # Compressed timestamp message
    data = BytesIO(initial_bytes=0b10000000.to_bytes(length=1, byteorder="big"))
    header = read_record_header(data)
    assert not header.is_definition_message
    assert not header.local_message_type == 1
    assert not header.is_developer_data
    assert header.is_compressed_timestamp_message
