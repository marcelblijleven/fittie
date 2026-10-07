import logging
from functools import cache

from fittie.profile.message_profile import (
    FieldProfile,
    MessageProfile,
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
    return MessageProfile(
        **{
            **source,
            "fields": {
                int(number): dict_to_field_profile(field)
                for number, field in source["fields"].items()
            },
        }
    )


def dict_to_field_profile(source: dict) -> FieldProfile:
    """Convert a field and its nested subfields without inspecting annotations."""
    subfields = source.get("subfields")
    return FieldProfile(
        **{
            **source,
            "subfields": [SubField(**subfield) for subfield in subfields]
            if subfields is not None
            else None,
        }
    )
