from pathlib import Path

import pytest
from fittie.fitfile.data_message import DataMessage
from fittie.fitfile.definition_message import DefinitionMessage
from fittie.fitfile.field_definitions import FieldDefinition
from fittie.fitfile.fitfile import FitFile
from fittie.fitfile.header import Header
from fittie.profile.base_types import BASE_TYPES
from fittie.fitfile.records import RecordHeader
from fittie.fitfile.utils.endianness import Endianness

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def small_fitfile():
    fitfile = FitFile(
        # TODO: add proper header data
        header=Header(
            length=12,
            protocol_version=1,
            profile_version=1,
            data_size=100,
            data_type="activity",
            crc=0x0000,
        ),
        data_messages={
            "file_id": [
                DataMessage(
                    header=RecordHeader(
                        is_definition_message=False,
                        is_compressed_timestamp_message=False,
                        is_developer_data=False,
                        time_offset=0,
                        local_message_type=0,
                    ),
                    fields={
                        "serial_number": None,
                        "time_created": 1046114779,
                        "manufacturer": 255,
                        "product": 0,
                        "number": 0,
                        "type": 4,
                    },
                )
            ],
            "record": [
                DataMessage(
                    header=RecordHeader(
                        is_definition_message=False,
                        is_compressed_timestamp_message=False,
                        is_developer_data=False,
                        time_offset=0,
                        local_message_type=0,
                    ),
                    fields={
                        "timestamp": 1046114799,
                        "position_lat": -138835324,
                        "position_long": 1992050244,
                        "distance": 1647,
                        "time_from_course": None,
                        "compressed_speed_distance": [None, None, None],
                        "heart_rate": 98,
                        "altitude": 2564,
                        "speed": 3765,
                        "power": 121,
                        "grade": None,
                        "cadence": 72,
                        "resistance": None,
                        "cycle_length": None,
                        "temperature": None,
                    },
                )
            ],
        },
        local_message_definitions={},
        developer_data={},
    )

    yield fitfile


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
        ],
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
        ],
    )


@pytest.fixture
def data_dir() -> Path:
    return DATA_DIR


@pytest.fixture
def load_fit_file():
    def _load_file(path: str | Path):
        with open(path, "rb") as file:
            yield file

    return _load_file
