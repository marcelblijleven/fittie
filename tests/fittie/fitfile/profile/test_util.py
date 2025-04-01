from fittie.profile import MessageProfile, FieldProfile, SubField
from fittie.profile.messages import MESSAGES
from fittie.profile.util import (
    get_message_profile,
    dict_to_message_profile,
    dict_to_field_profile,
)


def test_get_message_profile():
    # Test if all messages can be converted to a MessageProfile
    for number, value in MESSAGES.items():
        assert isinstance(
            message_profile := get_message_profile(number), MessageProfile
        )

        # Test if all fields are of type FieldProfile
        for field_number, field in message_profile.fields.items():
            assert isinstance(field, FieldProfile)

            # Test if all subfields are of type SubField
            for subfield in field.subfields:
                assert isinstance(subfield, SubField)
