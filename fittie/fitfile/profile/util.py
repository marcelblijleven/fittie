from dataclasses import fields
from functools import lru_cache

from fittie.fitfile.profile.message_profile import (
    MessageProfile,
    FieldProfile,
    SubField,
)
from fittie.fitfile.profile.messages import MESSAGES


@lru_cache(maxsize=None)
def get_message_profile(number: int) -> MessageProfile:
    """
    A cached helper method to retrieve data from messages.py as a MessageProfile by
    providing the message profile number.


    Notes:
        Replace lru_cache with cache when minimum Python version is 3.9
    """
    if number not in MESSAGES:
        raise ValueError(f'unknown message number "{number}"')

    return dict_to_message_profile(MESSAGES[number])


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
