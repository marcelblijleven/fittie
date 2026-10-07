from __future__ import annotations  # Added for type hints

from collections.abc import MutableMapping
from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

from fittie.fitfile.components import Accumulators
from fittie.fitfile.definition_message import DefinitionMessage
from fittie.fitfile.developer_values import DeveloperValues
from fittie.fitfile.field_definitions import read_developer_field
from fittie.fitfile.field_description import FieldDescription
from fittie.fitfile.message_decoder import MessageDecoder
from fittie.fitfile.utils.datastream import Streamable
from fittie.profile import FieldProfile

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

    __slots__ = ("header", "fields", "definition", "developer_fields", "native_fields")

    header: RecordHeader
    fields: dict[str, Any | None]

    def __init__(
        self,
        header: RecordHeader,
        fields: dict[str, Any | None],
        definition: DefinitionMessage | None = None,
        developer_fields: MutableMapping[tuple[int, int], Any] | None = None,
        native_fields: dict | None = None,
    ):
        self.header = header
        self.fields = fields
        self.definition = definition
        self.developer_fields = developer_fields
        self.native_fields = native_fields

    def get_field(self, field_name: str) -> Any | None:
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
    fields_raw: dict[str, Any],
    field_profile: FieldProfile,
    fields_with_components: list[str],
) -> list[str]:
    """
    Adds the field value of a DataMessage field that matches the provided field profile
    as an extra field to the DataMessage fields.

    For each subfield, it checks if the field name exists in the current fields dict,
    if so it checks if the field value equals the reference value number.

    If it finds a match, it adds the original field value to the fields dict, with the
    subfield name as key. The original value is retrieved from
    fields_raw, these values are not affected by scale / offset.

    For example {"product": 22} as fields, becomes {"product": 22, "garmin_product": 22}
    """

    subfield_names: list[str] = []

    if not field_profile.subfields:
        return subfield_names

    for subfield in field_profile.subfields:
        for reference in subfield.refs:
            if reference is None:
                continue
            if (
                field_value := fields_raw.get(cast(str, reference["field_name"]))
            ) is None:
                continue

            if reference["value_number"] == field_value:
                subfield_names.append(subfield.field_name)
                field_data = deepcopy(fields_raw[field_profile.field_name])

                if subfield.scale is not None or subfield.offset is not None:
                    field_data = apply_scale_and_offset(
                        field_data, subfield.scale, subfield.offset
                    )

                fields[subfield.field_name] = field_data

                if subfield.has_components:
                    fields_with_components.append(subfield.field_name)

    return subfield_names


def apply_scale_and_offset(
    field_data: Any,
    scale: int | float | list[int | float] | None,
    offset: int | float | None,
) -> Any:
    """
    Applies scale and offset to the provided value

    Value is divided by scale, default scale is 1
    Value is subtracted by offset, default offset is 0

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
    header: RecordHeader,
    message_definition: DefinitionMessage,
    developer_data: dict[int, dict[str, dict[int, FieldDescription]]],
    data: Streamable,
    accumulators: Accumulators | None = None,
) -> DataMessage:
    if accumulators is None:
        accumulators = {}
    compressed = header.is_compressed_timestamp_message
    plan = message_definition._decoders.get(compressed)
    if plan is None:
        plan = MessageDecoder(message_definition, compressed)
        message_definition._decoders[compressed] = plan
    fields = plan.read(data, accumulators)

    developers = None
    if message_definition.developer_field_definitions:
        values = []
        for dev in message_definition.developer_field_definitions:
            description = (
                developer_data.get(dev.data_index, {}).get("fields", {}).get(dev.number)
            )
            if description is None:
                value = data.read(dev.size)
                name = f"developer_{dev.data_index}_{dev.number}"
            else:
                value = read_developer_field(
                    description, dev, message_definition.endianness, data
                )
                name = description.field_name
            values.append(value)
            # Keep native values and both developers when names collide.
            key = (
                name
                if name not in fields
                else f"developer_{dev.data_index}_{dev.number}_{name}"
            )
            while key in fields:
                key = "_" + key
            fields[key] = value
        developers = DeveloperValues(message_definition.developer_keys, values)

    return DataMessage(header, fields, message_definition, developers, plan.last_native)
