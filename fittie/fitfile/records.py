from __future__ import annotations  # Added for type hints

import struct
from typing import Optional, Any

from fittie.utils.datastream import Streamable
from fittie.utils.exceptions import DecodeException
from fittie.fitfile.data_message import decode_data_message
from fittie.fitfile.definition_message import (
    DefinitionMessage,
    decode_definition_message,
)


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
    time_offset: Optional[int]

    def __init__(
        self,
        is_definition_message: bool,
        is_developer_data: bool,
        local_message_type: int,
        is_compressed_timestamp_message: bool,
        time_offset: Optional[int] = None,
    ):
        self.is_definition_message = is_definition_message
        self.is_developer_data = is_developer_data
        self.local_message_type = local_message_type
        self.is_compressed_timestamp_message = is_compressed_timestamp_message
        self.time_offset = time_offset

    def __str__(self) -> str:
        return (
            f"RecordHeader:{self.is_definition_message=}{self.is_developer_data=}"
            f"{self.local_message_type=}{self.time_offset=}"
        ).replace("self.", " ")


def read_record_header(data: Streamable) -> RecordHeader:
    try:
        (value,) = struct.unpack("B", data.read(1))

        # Use a bit mask to get bit 7 to determine if this is a normal (0) or
        # compressed timestamp header (1)
        if is_compressed_timestamp_message := bool(value >> 7):
            is_definition_message = False
            is_developer_data = False

            # Shift 5 places to the right to get bits 7, 6 and 5
            # then apply mask 0b011 to get bits 6 and 5
            local_message_type = (value >> 5) & 0b011

            # Apply mask 0b11111 to get bit 4, 3, 2, 1 and 0
            time_offset = value & 0b111111
        else:
            # Apply mask 0b1000000 to get bit 6 to determine if the message
            # is a definition message
            is_definition_message = bool(value & 0b1000000)

            # Apply mask 0b100000 to determine if message contains developer data
            is_developer_data = bool(value & 0b100000)

            # Bit 4 is reserved and always 0, extra validity check
            if bool(value & 0b10000):
                raise DecodeException(
                    detail="invalid byte received for record header",
                    position=data.tell(),
                )

            # Apply mask 0b1111 to get bit 3, 2, 1, and 0
            local_message_type = value & 0b1111
            time_offset = None

        return RecordHeader(
            is_definition_message=is_definition_message,
            is_developer_data=is_developer_data,
            local_message_type=local_message_type,
            is_compressed_timestamp_message=is_compressed_timestamp_message,
            time_offset=time_offset,
        )

    except struct.error as exc:
        raise DecodeException(
            detail="could not decode record header with provided data",
            position=data.tell(),
        ) from exc


def read_record(
    record_header: RecordHeader,
    definition_message: Optional[DefinitionMessage],
    developer_data: dict[int, dict[str, Any]],
    data: Streamable,
) -> Any:  # TODO: add ABC Message type
    if record_header.is_compressed_timestamp_message:
        # TODO
        ...
        return

    if record_header.is_developer_data:
        # TODO: check if this works correctly
        return decode_definition_message(record_header, data)

    if record_header.is_definition_message:
        return decode_definition_message(record_header, data)

    # Record is a data message
    if definition_message is None:
        raise DecodeException(
            detail=f"did not receive local message definition for number "
            f"{record_header.local_message_type}",
            position=data.tell(),
        )

    message = decode_data_message(
        record_header, definition_message, developer_data, data
    )
    return message
