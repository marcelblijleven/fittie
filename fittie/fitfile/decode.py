from __future__ import annotations  # Added for type hints

import struct

from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Optional, Union, cast

from fittie.fitfile.fitfile import FitFile
from fittie.fitfile.profile.fit_types import FIT_TYPES
from fittie.fitfile.util import is_definition_message, is_data_message
from fittie.fitfile.utils.datastream import DataStream, Streamable
from fittie.fitfile.utils.exceptions import DecodeException
from fittie.fitfile.data_message import DataMessage
from fittie.fitfile.definition_message import DefinitionMessage
from fittie.fitfile.field_description import FieldDescription
from fittie.fitfile.header import decode_header
from fittie.fitfile.profile.mesg_nums import MESG_NUMS
from fittie.fitfile.records import read_record_header, read_message


def decode(
    source: Union[str, Path, Streamable], calculate_crc: Optional[bool] = True
) -> FitFile:
    """
    Decode a fit file
    """
    with DataStream(source) as data:
        if not calculate_crc:
            # Don't calculate checksum
            data.should_calculate_crc = False

        header = decode_header(data)

        local_message_definitions: dict[int, DefinitionMessage] = {}
        developer_data: dict[int, dict[str, Any]] = {}
        messages: DefaultDict[str, list[DataMessage]] = defaultdict(list)

        while data.tell() < header.length + header.data_size:
            # Read message
            message = read_message(
                local_message_definitions,
                developer_data,
                data,
            )

            if isinstance(message, DefinitionMessage):
                local_message_definitions[message.header.local_message_type] = message
            else:
                index: int
                local_message_definition = local_message_definitions[
                    message.header.local_message_type
                ]

                if (
                    global_message_type := local_message_definition.global_message_type
                ) is None:
                    raise DecodeException(
                        detail="Missing global message type",
                        position=data.tell(),
                    )
                elif global_message_type == 207:
                    # Add developer data index
                    index = cast(int, message.fields["developer_data_index"])
                    developer_data[index] = message.fields
                    developer_data[index].update({"fields": {}})
                elif global_message_type == 206:
                    # Add field descriptions
                    index = cast(int, message.fields["developer_data_index"])
                    field = FieldDescription(**message.fields)
                    developer_data[index]["fields"][field.field_definition_number] = (
                        field
                    )

                if global_message_type in MESG_NUMS:
                    messages[MESG_NUMS[global_message_type]].append(message)
                else:
                    messages[f"unknown_{global_message_type}"].append(message)

        calculated_crc = data.calculated_crc
        (crc,) = struct.unpack("H", data.read(2))

        if calculate_crc and crc != calculated_crc:
            raise DecodeException(
                detail=(
                    "the calculated crc does not match the crc at the end of the file"
                ),
                position=data.tell(),
            )

    fitfile = FitFile(
        header=header,
        data_messages=messages,
        local_message_definitions=local_message_definitions,
        developer_data=developer_data,
    )

    return fitfile


def decode_file_type(source: Union[str, Path, Streamable]) -> str:
    """
    Only reads the File header, the first definition message and the first data message
    to retrieve the file type (e.g. activity, workout, weight etc.).

    This only works if the FIT file is encoded according to the FIT protocol best
    practices:
    - FIT file should start with a file header
    - A definition message for 'file_id'
    - A data message for 'file_id'
    """
    fields = {}

    with DataStream(source) as data:
        decode_header(data)
        local_message_definitions: dict[int, DefinitionMessage] = {}
        developer_data: dict = {}

        file_id_definition_message_record_header = read_record_header(data)

        file_id_definition_message = read_message(
            local_message_definitions,
            developer_data,
            data,
        )

        if not is_definition_message(file_id_definition_message):
            raise ValueError("Expected first message to be a definition message")

        if file_id_definition_message.global_message_type != 0:
            raise DecodeException(
                detail=(
                    "provided FIT file is possible not encoded correctly, the first "
                    "definition message does not have global_message_type 0 (file_id)"
                ),
                position=data.tell(),
            )

        local_message_definitions[
            file_id_definition_message_record_header.local_message_type
        ] = file_id_definition_message

        file_id_data_message = read_message(
            local_message_definitions,
            developer_data,
            data,
        )

        if not is_data_message(file_id_data_message):
            raise ValueError("Expected second message to be a file_id data message")

        fields = file_id_data_message.fields

    if not (file_type_number := fields["type"]) or not (
        file_type := FIT_TYPES["file"].values.get(file_type_number)
    ):
        raise DecodeException(
            detail=f"Invalid file type number received: {file_type_number}",
            position=data.tell(),
        )

    return file_type.value_name
