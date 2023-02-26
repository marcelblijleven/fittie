import struct

import pytest

from fittie.fitfile.definition_message import DefinitionMessage
from fittie.fitfile.field_definitions import FieldDefinition
from fittie.fitfile.profile.base_types import BASE_TYPES
from fittie.fitfile.records import RecordHeader
from fittie.utils.endianness import Endianness


@pytest.fixture
def record_1_definition_message():
    """Record 1 from Garmin FIT Protocol documentation"""
    yield DefinitionMessage(
        header=RecordHeader(
            is_definition_message=True,
            is_compressed_timestamp_message=False,
            is_developer_data=False,
            local_message_type=0,
        ),
        endianness=Endianness.LITTLE,
        global_message_type=0,
        field_definitions=[
            FieldDefinition(number=0, size=1, base_type=BASE_TYPES[0]),
            FieldDefinition(number=1, size=2, base_type=BASE_TYPES[132]),
            FieldDefinition(number=2, size=2, base_type=BASE_TYPES[132]),
            FieldDefinition(number=3, size=4, base_type=BASE_TYPES[140]),
            FieldDefinition(number=4, size=4, base_type=BASE_TYPES[134]),
        ]
    )


@pytest.fixture
def record_5_definition_message():
    yield DefinitionMessage(
        header=RecordHeader(
            is_definition_message=True,
            is_compressed_timestamp_message=False,
            is_developer_data=True,
            local_message_type=0,
        ),
        endianness=Endianness.LITTLE,
        global_message_type=206,
        field_definitions=[
            FieldDefinition(number=0, size=1, base_type=BASE_TYPES[2]),
            FieldDefinition(number=1, size=1, base_type=BASE_TYPES[2]),
            FieldDefinition(number=2, size=1, base_type=BASE_TYPES[2]),
            FieldDefinition(number=3, size=64, base_type=BASE_TYPES[7]),
            FieldDefinition(number=8, size=16, base_type=BASE_TYPES[7]),
        ]
    )