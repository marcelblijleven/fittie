from datetime import timezone

import pytest

from fittie import decode


@pytest.mark.parametrize("load_fit_file", ["fittie_minimal_file.fit"], indirect=True)
def test_minimal_file(load_fit_file):
    fitfile = decode(load_fit_file)

    header = fitfile.header
    assert header.length == 14
    assert header.protocol_version == 32
    assert header.profile_version == 2033
    assert header.data_size == 111

    developer_data = fitfile.developer_data.get(1)
    assert developer_data is not None
    cleaned_application_id = [num for num in developer_data["application_id"] if num]
    assert bytes(cleaned_application_id) == b"com.marcelblijleven.fittie"
    assert developer_data["application_version"] == 1337

    file_id = fitfile.file_id
    assert file_id["type"] == "activity"
    assert file_id["manufacturer"] == "development"
    assert file_id["product_name"] == "fittie-test"
    assert file_id["time_created"].tzinfo == timezone.utc
    ...


@pytest.mark.parametrize("load_fit_file", ["fittie_gearshifts.fit"], indirect=True)
def test_gearshifts(load_fit_file):
    fitfile = decode(load_fit_file)
    event_messages = fitfile.get_messages_by_type("event")
    assert len(event_messages) == 3

    # NOTE: this isn't exactly as expected, the field gear_change_data has
    # subfields and components, so it should be expanded into 4 fields.
    # Have not figured out a fix yet, could be an error in the Profile.xlsx
    # It expects a field name called 'event', but it is filled in as 'data'.
    assert event_messages[0].fields["data"] == 654380552
    assert event_messages[1].fields["data"] == 654380041
    assert event_messages[2].fields["data"] == 872549385


@pytest.mark.parametrize(
    "load_fit_file", ["fittie_developer_fields.fit"], indirect=True
)
def test_developer_fields(load_fit_file):
    fitfile = decode(load_fit_file)
    assert len(fitfile.developer_data.keys()) == 2

    fields = fitfile.developer_data[0]["fields"]
    assert (banana_field := fields[0]).field_name == "bananas_traversed"
    assert banana_field.units == "bananas"


@pytest.mark.parametrize("load_fit_file", ["fittie_settings_file.fit"], indirect=True)
def test_gearshifts(load_fit_file):
    fitfile = decode(load_fit_file)
    assert fitfile.file_type == "settings"
    assert (user_profile_messages := fitfile.data_messages.get("user_profile")) is not None
    assert user_profile_messages[0].fields["gender"] == 1
    assert user_profile_messages[0].fields["age"] == 33
    assert user_profile_messages[0].fields["weight"] == 80.1
    assert user_profile_messages[0].fields["friendly_name"] == "Fittie McFitface"


@pytest.mark.parametrize("load_fit_file", ["fittie_monitoring_file.fit"], indirect=True)
def test_monitoring_file(load_fit_file):
    """NOTE: This file has accumulated fields"""
    fitfile = decode(load_fit_file)
    assert fitfile.file_type == "monitoring_b"

    monitoring_messages = fitfile.get_messages_by_type("monitoring")

    assert len(monitoring_messages) == 24  # 24 hours

    for message in monitoring_messages:
        # Test if subfield has "scale" applied correctly
        assert message.fields["cycles"] * 2 == message.fields["steps"]
