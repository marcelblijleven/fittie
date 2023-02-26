import pytest

from io import BytesIO

from fittie.utils.exceptions import DecodeException
from fittie.fitfile.definition_message import (
    decode_definition_message,
    DefinitionMessage,
)
from fittie.fitfile.field_definitions import DeveloperFieldDefinition
from fittie.fitfile.records import RecordHeader
from fittie.utils.endianness import Endianness


def test_decode_definition_message_example_record_1():
    """Example from Garmin FIT Protocol documentation"""
    header = RecordHeader(
        is_definition_message=True,
        is_compressed_timestamp_message=False,
        is_developer_data=False,
        local_message_type=0,
    )

    reserved = (0).to_bytes(length=1, byteorder="little")
    architecture = (0).to_bytes(length=1, byteorder="little")
    global_message_number = (0).to_bytes(length=2, byteorder="little")
    number_of_fields = (5).to_bytes(length=1, byteorder="little")

    # Field 0
    field_0 = bytearray([0, 1, 0])
    field_1 = bytearray([1, 2, 132])
    field_2 = bytearray([2, 2, 132])
    field_3 = bytearray([3, 4, 140])
    field_4 = bytearray([4, 4, 134])

    data = BytesIO(
        reserved
        + architecture
        + global_message_number
        + number_of_fields
        + field_0
        + field_1
        + field_2
        + field_3
        + field_4
    )
    definition_message = decode_definition_message(header, data)

    assert definition_message.global_message_type == 0
    assert len(definition_message.field_definitions) == 5
    assert definition_message.endianness == Endianness.LITTLE
    assert definition_message.developer_field_definitions == []
    assert definition_message.number_of_fields == 5


def test_decode_definition_message_invalid_record_header():
    header = RecordHeader(
        is_definition_message=False,  # set to False
        is_compressed_timestamp_message=False,
        is_developer_data=False,
        local_message_type=0,
    )

    data = BytesIO()

    with pytest.raises(DecodeException) as excinfo:
        decode_definition_message(header, data)

    assert (
        "tried to decode definition message with a non-definition message header"
        in str(excinfo.value)
    )


def test_decode_definition_message_invalid_reserved_bit():
    header = RecordHeader(
        is_definition_message=True,
        is_compressed_timestamp_message=False,
        is_developer_data=False,
        local_message_type=0,
    )

    data = BytesIO(bytearray([1]))

    with pytest.raises(DecodeException) as excinfo:
        decode_definition_message(header, data)

    assert "received invalid data for a definition message" in str(excinfo.value)


def test_get_developer_field_definition():
    developer_field_definition = DeveloperFieldDefinition(
        data_index=1, number=2, size=1
    )
    definition_message = DefinitionMessage(
        header=RecordHeader(
            is_definition_message=True,
            is_developer_data=False,
            is_compressed_timestamp_message=False,
            local_message_type=0,
        ),
        endianness=Endianness.LITTLE,
        global_message_type=0,
        field_definitions=[],
        developer_field_definitions=[developer_field_definition],
    )

    assert (
        definition_message.get_developer_field_definition(data_index=1, number=2)
        == developer_field_definition
    )

    assert (
        definition_message.get_developer_field_definition(data_index=1, number=1)
        is None
    )
