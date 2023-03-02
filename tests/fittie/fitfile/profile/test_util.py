from fittie.fitfile.profile import MessageProfile, FieldProfile, SubField
from fittie.fitfile.profile.messages import MESSAGES
from fittie.fitfile.profile.util import (
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


def test_dict_to_message_profile():
    # Messages number 0 is file_id, this message has fields with subfields
    message = MESSAGES[0]
    message_profile = dict_to_message_profile(MESSAGES[0])

    assert isinstance(message_profile, MessageProfile)
    assert message_profile.name == message["name"]

    # Check fields
    for field in message_profile.fields.values():
        assert isinstance(field, FieldProfile)

    assert message_profile.group == message["group"]


def test_dict_to_field_profile():
    # Field 2 of message 0 has subfields
    field = MESSAGES[0]["fields"][2]
    field_profile = dict_to_field_profile(field)

    assert isinstance(field_profile, FieldProfile)
    assert field_profile.field_name == "product"

    assert field_profile.field_name == field["field_name"]
    assert field_profile.field_type == field["field_type"]
    assert field_profile.components == field["components"]
    assert field_profile.scale == field["scale"]
    assert field_profile.offset == field["offset"]
    assert field_profile.units == field["units"]
    assert field_profile.bits == field["bits"]
    assert field_profile.accumulate == field["accumulate"]

    assert len(field_profile.subfields) == len(field["subfields"])

    for subfield in field_profile.subfields:
        assert isinstance(subfield, SubField)

    assert field_profile.comment == field["comment"]
