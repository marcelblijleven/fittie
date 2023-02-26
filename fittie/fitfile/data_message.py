from __future__ import annotations  # Added for type hints

from typing import Any, Optional, TYPE_CHECKING

from fittie.utils.datastream import Streamable
from fittie.utils.exceptions import DecodeException
from fittie.fitfile.definition_message import DefinitionMessage
from fittie.fitfile.field_definitions import read_field, read_developer_field
from fittie.fitfile.field_description import FieldDescription
from fittie.fitfile.profile.util import get_message_profile


if TYPE_CHECKING:
    from fittie.fitfile.records import RecordHeader


class DataMessage:
    """
    Contains a local message type and populated data fields as described by the
    preceding definition message.

    There are two types of data message:
        Normal Data Message
        Compressed Timestamp Data Message

    Related DefinitionMessages and DataMessages share a local message type
    """

    header: "RecordHeader"
    fields: dict[str, Optional[Any]]

    def __init__(self, header: "RecordHeader", fields: dict[str, Optional[Any]]):
        self.header = header
        self.fields = fields

    def get_field(self, field_name: str) -> Optional[Any]:
        """Retrieve a field by key from fields"""
        return self.fields.get(field_name, None)

    @property
    def local_message_type(self) -> int:
        """Retrieves the local message type from the message header"""
        return self.header.local_message_type

    def __str__(self) -> str:
        return f"DataMessage:{self.fields}".replace("self.", " ")

    def __repr__(self) -> str:
        return str(self)


def decode_data_message(
    header: "RecordHeader",
    message_definition: DefinitionMessage,
    developer_data: dict[int, dict[str, dict[int, FieldDescription]]],
    data: Streamable,
) -> DataMessage:
    message_profile = get_message_profile(message_definition.global_message_type)

    fields: dict[str, Any] = {}

    for field in message_definition.field_definitions:
        field_profile = message_profile.fields[field.number]
        field_data = read_field(
            field_definition=field,
            # field_profile=field_profile,
            endianness=message_definition.endianness,
            data=data,
        )

        # TODO: components, accumulate etc (from field_profile?)
        fields[field_profile.field_name] = field_data

    if message_definition.developer_field_definitions and not developer_data:
        raise DecodeException(
            detail="definition message contains developer fields, "
            "but no field descriptions are provided",
            position=data.tell(),
        )

    for field in message_definition.developer_field_definitions:
        try:
            field_description = developer_data[field.data_index]["fields"][field.number]
        except KeyError:
            raise DecodeException(
                detail=f"no field description found for field {field}",
                position=data.tell(),
            )

        developer_field_definition = message_definition.get_developer_field_definition(
            data_index=field_description.developer_data_index,
            number=field_description.field_definition_number,
        )

        if not developer_field_definition:
            raise DecodeException(
                detail=f"no developer field definition found for field {field}",
                position=data.tell(),
            )

        field_data = read_developer_field(
            field_description=field_description,
            field_definition=developer_field_definition,
            endianness=message_definition.endianness,
            data=data,
        )

        fields[field_description.field_name] = field_data

    return DataMessage(header=header, fields=fields)
