from fittie.profile import FieldProfile, MessageProfile, SubField
from fittie.profile.messages import MESSAGES
from fittie.profile.util import (
    get_message_profile,
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


def test_nested_profile_conversion_does_not_depend_on_annotation_strings():
    from dataclasses import asdict

    from fittie.profile.util import dict_to_message_profile

    expected = MessageProfile(
        name="example",
        group=None,
        fields={
            0: FieldProfile("data", "uint32", subfields=[SubField("sub", "uint32", [])])
        },
    )
    assert dict_to_message_profile(asdict(expected)) == expected
