from __future__ import annotations  # Added for type hints
import logging
from copy import deepcopy
from typing import Any, Optional, TYPE_CHECKING

from fittie.fitfile.profile import FieldProfile
from fittie.utils.datastream import Streamable
from fittie.utils.exceptions import DecodeException
from fittie.fitfile.definition_message import DefinitionMessage
from fittie.fitfile.field_definitions import read_field, read_developer_field
from fittie.fitfile.field_description import FieldDescription
from fittie.fitfile.profile.util import get_message_profile

logger = logging.getLogger(__name__)

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


def add_subfields_to_fields(
    fields: dict[str, Any],
    field_profile: FieldProfile,
    fields_with_components: list[str],
) -> list[str]:
    """
    Adds the field value of a DataMessage field that matches the provided field profile
    as an extra field to the DataMessage fields.

    For each subfield, it checks if the field name exists in the current fields dict,
    if so it checks if the field value equals the reference value number.

    If it finds a match, it adds the original field value to the fields dict, with the
    subfield name as key.

    For example {"product": 22} as fields, becomes {"product": 22, "garmin_product": 22}
    """

    subfield_names = []

    for subfield in field_profile.subfields:
        for reference in subfield.refs:
            if not (field_value := fields.get(reference["field_name"])):
                continue

            if reference["value_number"] == field_value:
                subfield_names.append(subfield.field_name)
                fields[subfield.field_name] = deepcopy(fields[field_profile.field_name])

                if subfield.has_components:
                    fields_with_components.append(subfield.field_name)

    return subfield_names


def apply_scale_and_offset(
    field_data: Any, scale: Optional[int], offset: Optional[int]
) -> Any:
    """
    Applies scale and offset to the provided value

    Value is divided by scale, default scale is 1
    Value is subtracted by ofset, default offset is 0

    Value can be a single value, or list of value
    Scale can be a single value, or list of value
    Offset is single value
    """
    if field_data is None:
        return field_data

    scale = scale or 1
    offset = offset or 0

    if not isinstance(field_data, list):
        return field_data / scale - offset

    if isinstance(scale, list):
        if len(scale) != len(field_data):
            return field_data

        return [apply_scale_and_offset(d, s, offset) for d, s in zip(field_data, scale)]

    return [apply_scale_and_offset(data, scale, offset) for data in field_data]


def decode_data_message(
    header: "RecordHeader",
    message_definition: DefinitionMessage,
    developer_data: dict[int, dict[str, dict[int, FieldDescription]]],
    data: Streamable,
) -> DataMessage:
    message_profile = get_message_profile(message_definition.global_message_type)

    fields: dict[str, Any] = {}
    fields_with_subfields: dict[str, FieldProfile] = {}
    fields_with_components: list[str] = []
    subfield_names = []

    for field in message_definition.field_definitions:
        field_profile = message_profile.fields[field.number]
        field_data = read_field(
            field_definition=field,
            endianness=message_definition.endianness,
            data=data,
        )

        if field_profile and (
            field_profile.scale is not None or field_profile.offset is not None
        ):
            field_data = apply_scale_and_offset(
                field_data, scale=field_profile.scale, offset=field_profile.offset
            )

        fields[field_profile.field_name] = field_data

        if field_profile.has_subfields:
            fields_with_subfields[field_profile.field_name] = field_profile
        if field_profile.has_components:
            fields_with_components.append(field_profile.field_name)

    # TODO: components, accumulate etc (from field_profile?)
    if fields_with_subfields:
        for field, field_profile in fields_with_subfields.items():
            subfield_names += add_subfields_to_fields(
                fields, field_profile, fields_with_components
            )
    if fields_with_components:
        logger.debug(f"components not implemented yet, {fields_with_components=}")

    # if field_profile.accumulate:
    #     ...

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
