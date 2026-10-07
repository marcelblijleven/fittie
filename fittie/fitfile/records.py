from __future__ import annotations  # Added for type hints

from dataclasses import dataclass
from typing import Any

from fittie.fitfile.components import Accumulators
from fittie.fitfile.data_message import DataMessage, decode_data_message
from fittie.fitfile.definition_message import (
    DefinitionMessage,
    decode_definition_message,
)
from fittie.fitfile.utils.datastream import Streamable
from fittie.fitfile.utils.exceptions import DecodeException


@dataclass(frozen=True, slots=True)
class RecordHeader:
    """
    A one byte header to determine of the record is either a DefinitionMessage,
    Normal Data Message or a Compressed Timestamp Data Message

    Normal header
    - Bit 0-3, Value 0-15: Local message type
    - Bit 4, Value 0: Reserved
    - Bit 5, Value 0 or 1: Message Type Specific (e.g. Developer Data Flag)
    - Bit 6, Value 0 or 1: Message Type, 1: Definition Message, 0: Data Message
    - Bit 7, Value 0, Header type: Normal header

    Compressed timestamp header
    - Bit 0-4, Value 0-31, Time offset
    - Bit 5-6, Value 0-3: Local Message Type
    - Bit 7, Value 1: Compressed timestamp header
    """

    is_definition_message: bool
    is_developer_data: bool
    local_message_type: int
    is_compressed_timestamp_message: bool
    time_offset: int | None = None

    def __str__(self) -> str:
        return (
            f"RecordHeader:{self.is_definition_message=}{self.is_developer_data=}"
            f"{self.local_message_type=}{self.time_offset=}"
        ).replace("self.", " ")


# Headers contain only immutable byte-derived attributes and can be shared.
_RECORD_HEADERS = tuple(
    RecordHeader(
        is_definition_message=bool(value & 0x40) if value < 128 else False,
        is_developer_data=bool(value & 0x20) if value < 128 else False,
        local_message_type=value & 0x0F if value < 128 else (value >> 5) & 3,
        is_compressed_timestamp_message=value >= 128,
        time_offset=value & 31 if value >= 128 else None,
    )
    for value in range(256)
)


def read_record_header(data: Streamable) -> RecordHeader:
    raw = data.read(1)
    if not raw:
        raise DecodeException(
            detail="could not decode record header", position=data.tell()
        )
    return _RECORD_HEADERS[raw[0]]


def read_message(
    local_message_definitions: dict[int, DefinitionMessage],
    developer_data: dict[int, dict[str, Any]],
    data: Streamable,
    previous_timestamp: int | None = None,
    accumulators: Accumulators | None = None,
) -> DefinitionMessage | DataMessage:
    record_header = read_record_header(data)
    definition_message = local_message_definitions.get(record_header.local_message_type)

    if record_header.is_developer_data or record_header.is_definition_message:
        return decode_definition_message(record_header, data)

    # Record is a data message
    if definition_message is None:
        raise DecodeException(
            detail=f"did not receive local message definition for number "
            f"{record_header.local_message_type}",
            position=data.tell(),
        )

    message = decode_data_message(
        record_header, definition_message, developer_data, data, accumulators
    )

    if record_header.is_compressed_timestamp_message:
        if previous_timestamp is None or record_header.time_offset is None:
            raise DecodeException(
                detail="compressed timestamp requires a preceding full timestamp",
                position=data.tell(),
            )
        offset = record_header.time_offset
        timestamp = (previous_timestamp & ~0x1F) + offset
        if offset < (previous_timestamp & 0x1F):
            timestamp += 0x20
        message.fields["timestamp"] = timestamp
    return message
