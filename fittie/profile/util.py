import logging
from dataclasses import fields
from functools import cache

from fittie.profile.message_profile import (
    MessageProfile,
    FieldProfile,
    SubField,
)
from fittie.profile.messages import MESSAGES

logger = logging.getLogger("fittie")


@cache
def get_message_profile(number: int) -> MessageProfile | None:
    """
    A cached helper method to retrieve data from messages.py as a MessageProfile by
    providing the message profile number.
    """
    if number not in MESSAGES:
        logger.debug(f'unknown message number "{number}"')
        return None

    #    return dict_to_message_profile(MESSAGES[number])
    return MESSAGES[number]


def dict_to_message_profile(source: dict) -> MessageProfile:
    """
    Converts a nested dict to a MessageProfile, with FieldProfiles
    """
    raw = {}
    field_types = {f.name: f.type for f in fields(MessageProfile)}

    for key, value in source.items():
        if field_types[key] != "dict[int, FieldProfile]":
            raw[key] = value
            continue

        raw_fields = {}
        for field_key, field_value in value.items():
            raw_fields[field_key] = dict_to_field_profile(field_value)

        raw[key] = raw_fields

    return MessageProfile(**raw)


def dict_to_field_profile(source: dict) -> FieldProfile:
    """
    Converts a nested dict to a FieldProfile, with SubFields
    """
    raw = {}
    field_types = {f.name: f.type for f in fields(FieldProfile)}

    for key, value in source.items():
        if field_types[key] != "Optional[list[SubField]]":
            raw[key] = value
            continue

        raw_subfields = []
        for subfield in value:
            raw_subfields.append(SubField(**subfield))

        raw[key] = raw_subfields

    return FieldProfile(**raw)
