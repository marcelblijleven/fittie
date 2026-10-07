from __future__ import annotations  # Added for type hints

import struct
from collections import defaultdict
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from fittie.fitfile.components import Accumulators
from fittie.fitfile.data_message import DataMessage
from fittie.fitfile.definition_message import DefinitionMessage
from fittie.fitfile.field_description import FieldDescription
from fittie.fitfile.fitfile import FitFile
from fittie.fitfile.header import decode_header
from fittie.fitfile.options import DEFAULT_OPTIONS, DecodeOptions
from fittie.fitfile.processing import convert_fields, native_overrides
from fittie.fitfile.records import read_message
from fittie.fitfile.util import is_data_message, is_definition_message
from fittie.fitfile.utils.datastream import DataStream, Streamable
from fittie.fitfile.utils.exceptions import DecodeException
from fittie.profile.fit_types import FIT_TYPES
from fittie.profile.mesg_nums import MESG_NUMS


def decode(
    source: str | Path | Streamable,
    calculate_crc: bool = True,
    *,
    options: DecodeOptions = DEFAULT_OPTIONS,
    message_listener: Callable[[int, dict], None] | None = None,
    field_description_listener: Callable[[FieldDescription, dict], None] | None = None,
) -> list[FitFile]:
    """Decode all FIT members. Numeric enums/timestamps are retained by default."""
    return list(
        iter_files(
            source,
            calculate_crc,
            options=options,
            message_listener=message_listener,
            field_description_listener=field_description_listener,
        )
    )


def iter_files(
    source: str | Path | Streamable,
    calculate_crc: bool = True,
    *,
    options: DecodeOptions = DEFAULT_OPTIONS,
    message_listener: Callable[[int, dict], None] | None = None,
    field_description_listener: Callable[[FieldDescription, dict], None] | None = None,
) -> Iterator[FitFile]:
    """Yield each validated FIT member, retaining only the current member."""
    yield from _decode_events(
        source,
        calculate_crc,
        options,
        message_listener,
        field_description_listener,
        False,
    )


def iter_messages(
    source: str | Path | Streamable,
    calculate_crc: bool = True,
    *,
    options: DecodeOptions = DEFAULT_OPTIONS,
    message_listener: Callable[[int, dict], None] | None = None,
    field_description_listener: Callable[[FieldDescription, dict], None] | None = None,
) -> Iterator[DataMessage]:
    """Yield wire-order messages without retaining the file's message lists.

    CRC is verified at each member's end. Earlier yielded values are provisional
    until iteration finishes. Closing the iterator closes owned files only.
    Heart-rate merging requires complete-member buffering; use iter_files for it.
    """
    if options.merge_heart_rates:
        raise ValueError("iter_messages cannot merge heart rates; use iter_files")
    yield from _decode_events(
        source,
        calculate_crc,
        options,
        message_listener,
        field_description_listener,
        True,
    )


def _decode_events(
    source, calculate_crc, options, listener, description_listener, streaming
):
    with DataStream(source) as data:
        data.should_calculate_crc = calculate_crc
        convert = options.convert_types_to_strings or options.convert_datetimes_to_dates
        while True:
            data.reset_crc()
            first_byte = data.read(1, allow_eof=True)
            if not first_byte:
                break
            try:
                header = decode_header(data, first_byte=first_byte)
                data_end = data.tell() + header.data_size
                data.limit = data_end
                previous_timestamp = None
                accumulators: Accumulators = {}
                definitions: dict[int, DefinitionMessage] = {}
                schemas: dict[tuple, DefinitionMessage] = {}
                developer_data: dict[int, dict[str, Any]] = {}
                messages: defaultdict[str, list[DataMessage]] = defaultdict(list)
                ordered: list[DataMessage] = []
                while data.tell() < data_end:
                    message = read_message(
                        definitions,
                        developer_data,
                        data,
                        previous_timestamp=previous_timestamp,
                        accumulators=accumulators,
                    )
                    if isinstance(message, DefinitionMessage):
                        if not streaming:
                            signature = (
                                message.header.local_message_type,
                                message.global_message_type,
                                message.endianness,
                                tuple(
                                    (f.number, f.size, f.wire_type)
                                    for f in message.field_definitions
                                ),
                                tuple(
                                    (f.number, f.size, f.data_index)
                                    for f in message.developer_field_definitions
                                ),
                            )
                            message = schemas.setdefault(signature, message)
                        message.options = options
                        definitions[message.header.local_message_type] = message
                        continue
                    number = definitions[
                        message.header.local_message_type
                    ].global_message_type
                    timestamp = message.fields.get("timestamp")
                    if isinstance(timestamp, int):
                        previous_timestamp = timestamp
                    if number == 207:
                        index = message.fields.get("developer_data_index")
                        if isinstance(index, int):
                            existing = developer_data.get(index, {}).get("fields", {})
                            previous = developer_data.get(index, {})
                            if previous.get(
                                "application_id"
                            ) is not None and previous.get(
                                "application_id"
                            ) != message.fields.get("application_id"):
                                existing = {}
                            developer_data[index] = {
                                **message.fields,
                                "fields": existing,
                            }
                    elif number == 206:
                        index = message.fields.get("developer_data_index")
                        field_num = message.fields.get("field_definition_number")
                        if isinstance(index, int) and isinstance(field_num, int):
                            description = FieldDescription(**message.fields)
                            developer = developer_data.setdefault(index, {"fields": {}})
                            developer["fields"][field_num] = description
                            if description_listener:
                                description_listener(description, developer)
                    if options.apply_native_overrides:
                        native_overrides(message, developer_data)
                    if convert and number not in (206, 207):
                        convert_fields(number, message.fields, options)
                    if listener and not options.merge_heart_rates:
                        listener(number, message.fields)
                    if streaming:
                        yield message
                    else:
                        messages[MESG_NUMS.get(number, f"unknown_{number}")].append(
                            message
                        )
                        ordered.append(message)
                data.limit = None
                calculated_crc = data.calculated_crc
                (crc,) = struct.unpack("<H", data.read(2))
                if calculate_crc and crc != calculated_crc:
                    raise DecodeException(
                        detail="the calculated crc does not match the crc at the end of the file",
                        position=data.tell(),
                    )
                if not streaming:
                    if options.merge_heart_rates:
                        from fittie.fitfile.heart_rate import merge_heart_rates

                        merge_heart_rates(
                            [m.fields for m in messages.get("hr", ())],
                            [m.fields for m in messages.get("record", ())],
                        )
                        if listener:
                            for message in ordered:
                                assert message.definition is not None
                                listener(
                                    message.definition.global_message_type,
                                    message.fields,
                                )
                    yield FitFile(
                        header, messages, definitions, developer_data, ordered
                    )
            except EOFError as exc:
                raise DecodeException(detail=str(exc), position=data.tell()) from exc


def decode_file_type(source: str | Path | Streamable) -> str:
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
            file_id_definition_message.header.local_message_type
        ] = file_id_definition_message

        file_id_data_message = read_message(
            local_message_definitions,
            developer_data,
            data,
        )

        if not is_data_message(file_id_data_message):
            raise ValueError("Expected second message to be a file_id data message")

        fields = file_id_data_message.fields
        position = data.tell()

    file_type_number = fields.get("type")
    file_type = (
        FIT_TYPES["file"].values.get(file_type_number)
        if isinstance(file_type_number, int)
        else None
    )
    if file_type is None:
        raise DecodeException(
            detail=f"Invalid file type number received: {file_type_number}",
            position=position,
        )

    return file_type.value_name
