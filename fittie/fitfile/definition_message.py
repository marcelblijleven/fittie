from __future__ import annotations  # Added for type hints

import struct
from typing import TYPE_CHECKING

from fittie.fitfile.field_definitions import (
    DeveloperFieldDefinition,
    FieldDefinition,
    decode_developer_field_definition,
    decode_field_definition,
)
from fittie.fitfile.options import DEFAULT_OPTIONS
from fittie.fitfile.utils.datastream import Streamable
from fittie.fitfile.utils.endianness import Endianness
from fittie.fitfile.utils.exceptions import DecodeException

if TYPE_CHECKING:
    from fittie.fitfile.message_decoder import MessageDecoder
    from fittie.fitfile.records import RecordHeader


class DefinitionMessage:
    """
    Defines a local message type and associates it to a specific FIT message,
    and then designate the byte alignment and field contents of the
    upcoming data message.

    Definition messages have a fixed content of 5 bytes, and a variable content part
    which contains the field definitions (3 bytes per field)

    Fixed content:
    - Reserved: 1 Byte
    - Architecture: 1 Byte
    - Global message number: 2 bytes
    - Number of fields: 1 byte
    """

    header: RecordHeader
    endianness: str
    global_message_type: int
    number_of_fields: int
    field_definitions: list[FieldDefinition]
    number_of_developer_fields: int
    developer_field_definitions: list[DeveloperFieldDefinition]

    def __init__(
        self,
        header: RecordHeader,
        endianness: str,
        global_message_type: int,
        field_definitions: list[FieldDefinition],
        developer_field_definitions: list[DeveloperFieldDefinition] | None = None,
    ):
        self.options = DEFAULT_OPTIONS
        self._decoders: dict[bool, MessageDecoder] = {}
        self.header = header
        self.endianness = endianness
        self.global_message_type = global_message_type
        self.number_of_fields = len(field_definitions)
        self.field_definitions = field_definitions

        if developer_field_definitions is None:
            developer_field_definitions = []

        self.number_of_developer_fields = len(developer_field_definitions)
        self.developer_field_definitions = developer_field_definitions
        self.developer_keys = tuple(
            (field.data_index, field.number) for field in developer_field_definitions
        )

    def get_developer_field_definition(
        self, data_index: int, number: int
    ) -> DeveloperFieldDefinition | None:
        """
        Retrieve a DeveloperFieldDefinition by data index and number.
        If no definition is found, None will be returned
        """
        for definition in self.developer_field_definitions:
            if definition.number == number and definition.data_index == data_index:
                return definition

        return None

    def __str__(self) -> str:
        return (
            f"DefinitionMessage:{self.endianness=}{self.global_message_type=}"
            f"{self.field_definitions=}{self.developer_field_definitions=}"
        ).replace("self.", " ")

    def __repr__(self) -> str:
        return str(self)


def decode_definition_message(
    header: RecordHeader, data: Streamable
) -> DefinitionMessage:
    if not header.is_definition_message:
        raise DecodeException(
            detail="tried to decode definition message with a non-definition message "
            "header",
            position=data.tell(),
        )

    try:
        (reserved,) = struct.unpack("B", data.read(1))

        if bool(reserved):
            raise DecodeException(
                detail="received invalid data for a definition message",
                position=data.tell(),
            )

        (architecture,) = struct.unpack("B", data.read(1))
        if architecture not in (0, 1):
            raise DecodeException(detail="invalid architecture", position=data.tell())
        endianness = Endianness.BIG if architecture else Endianness.LITTLE
        (global_message_type,) = struct.unpack(f"{endianness}H", data.read(2))
        (number_of_fields,) = struct.unpack("B", data.read(1))

        field_definitions: list[FieldDefinition] = []
        developer_field_definitions: list[DeveloperFieldDefinition] | None = None

        for field in range(number_of_fields):
            field_definitions.append(decode_field_definition(data))

        if header.is_developer_data:
            developer_field_definitions = []
            (number_of_developer_fields,) = struct.unpack("B", data.read(1))

            for field in range(number_of_developer_fields):
                developer_field_definitions.append(
                    decode_developer_field_definition(data)
                )

        if len({f.number for f in field_definitions}) != len(field_definitions):
            raise DecodeException(
                detail="duplicate native field definition", position=data.tell()
            )
        developer_keys = [
            (f.data_index, f.number) for f in developer_field_definitions or ()
        ]
        if len(set(developer_keys)) != len(developer_keys):
            raise DecodeException(
                detail="duplicate developer field definition", position=data.tell()
            )
        return DefinitionMessage(
            header=header,
            endianness=endianness,
            global_message_type=global_message_type,
            field_definitions=field_definitions,
            developer_field_definitions=developer_field_definitions,
        )

    except struct.error as exc:
        raise DecodeException(
            detail="could not decode definition message with provided data",
            position=data.tell(),
        ) from exc
