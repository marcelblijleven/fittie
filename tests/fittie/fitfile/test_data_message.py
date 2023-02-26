from io import BytesIO

from fittie.fitfile.data_message import decode_data_message
from fittie.fitfile.records import RecordHeader


def test_decode_data_message(record_1_definition_message):
    # Expect record 2
    header = RecordHeader(
        is_definition_message=False,
        is_developer_data=False,
        is_compressed_timestamp_message=False,
        local_message_type=0
    )
    data = b'\x04\x0f\x00\x16\x00\xd2\x04\x00\x00(\xc6\n%'
    data_message = decode_data_message(
        header,
        record_1_definition_message,
        developer_data={},
        data=BytesIO(data)
    )
    assert data_message.fields == {
        "type": 4,
        "manufacturer": 15,
        "product": 22,
        "serial_number": 1234,
        "time_created": 621463080,
    }


def test_decode_data_message_with_developer_fields(record_5_definition_message):
    # Expect record 6
    header = RecordHeader(
        is_definition_message=False,
        is_developer_data=False,
        is_compressed_timestamp_message=False,
        local_message_type=0
    )
    data = (
        b'\x00\x00\x01'
        b'doughnuts earned\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'doughnuts\x00\x00\x00\x00\x00\x00\x00'
    )
    data_message = decode_data_message(
        header,
        record_5_definition_message,
        developer_data={},
        data=BytesIO(data)
    )
    assert data_message.fields == {
        "developer_data_index": 0,
        "fit_base_type_id": 1,
        "field_definition_number": 0,
        "field_name": "doughnuts earned",
        "units": "doughnuts"
    }
