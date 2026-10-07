"""Optional semantic conversions, applied after native protocol processing."""

from datetime import datetime, timedelta, timezone
from functools import cache

from fittie.profile.fit_types import FIT_TYPES
from fittie.profile.messages import MESSAGES

FIT_EPOCH = datetime(1989, 12, 31, tzinfo=timezone.utc)


@cache
def field_types(number: int) -> dict[str, str]:
    types = {
        "timestamp": "date_time",
        "message_index": "message_index",
        "part_index": "uint32",
    }
    profile = MESSAGES.get(number)
    if profile:
        for field in profile.fields.values():
            types[field.field_name] = field.field_type
            for sub in field.subfields or ():
                types[sub.field_name] = sub.field_type
    return types


def convert_fields(number, fields, options):
    for name, type_name in field_types(number).items():
        if name not in fields:
            continue
        field_type = FIT_TYPES.get(type_name)

        def convert(value):
            if value is None or not isinstance(value, (int, float)):
                return value
            if options.convert_datetimes_to_dates and type_name == "date_time":
                # Values below 0x10000000 represent device uptime, not UTC dates.
                return (
                    FIT_EPOCH + timedelta(seconds=value)
                    if value >= 0x10000000
                    else value
                )
            if options.convert_types_to_strings and field_type:
                enum = field_type.values.get(value) if isinstance(value, int) else None
                return enum.value_name if enum else value
            return value

        value = fields[name]
        fields[name] = (
            [convert(item) for item in value]
            if isinstance(value, list)
            else convert(value)
        )


def native_overrides(message, developer_data):
    if not message.developer_fields or message.definition is None:
        return
    number = message.definition.global_message_type
    profile = MESSAGES.get(number)
    if profile is None:
        return
    for (index, field_num), value in message.developer_fields.items():
        description = developer_data.get(index, {}).get("fields", {}).get(field_num)
        if description is None or description.native_message_number not in (
            None,
            number,
        ):
            continue
        target = profile.fields.get(description.native_field_number)
        if target is not None and value is not None:
            message.fields[target.field_name] = value
