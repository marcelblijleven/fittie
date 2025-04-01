from datetime import timezone

import pytest

from fittie import decode


def garmin_sdk_fitfile_names():
    from tests.conftest import DATA_DIR
    files = (DATA_DIR / "from_garmin_sdk").glob("*.fit")

    return [f.name for f in files]


def test_minimal_file(load_fit_file, data_dir):
    fitfiles = decode(data_dir / "fittie_minimal_file.fit")
    assert len(fitfiles) == 1
    for fitfile in fitfiles:

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


def test_gearshifts(load_fit_file, data_dir):
    fitfiles = decode(data_dir / "fittie_gearshifts.fit")
    assert len(fitfiles) == 1
    for fitfile in fitfiles:
        event_messages = fitfile.get_messages_by_type("event")
        assert len(event_messages) == 3

        # NOTE: this isn't exactly as expected, the field gear_change_data has
        # subfields and components, so it should be expanded into 4 fields.
        # Have not figured out a fix yet, could be an error in the Profile.xlsx
        # It expects a field name called 'event', but it is filled in as 'data'.
        assert event_messages[0].fields["data"] == 654380552
        assert event_messages[1].fields["data"] == 654380041
        assert event_messages[2].fields["data"] == 872549385


def test_developer_fields(load_fit_file, data_dir):
    fitfiles = decode(data_dir / "fittie_developer_fields.fit")
    assert len(fitfiles) == 1
    for fitfile in fitfiles:
        assert len(fitfile.developer_data.keys()) == 2

        fields = fitfile.developer_data[0]["fields"]
        assert (banana_field := fields[0]).field_name == "bananas_traversed"
        assert banana_field.units == "bananas"


def test_settings_file(load_fit_file, data_dir):
    fitfiles = decode(data_dir / "fittie_settings_file.fit")
    assert len(fitfiles) == 1
    for fitfile in fitfiles:
        assert fitfile.file_type == "settings"
        assert (
            user_profile_messages := fitfile.data_messages.get("user_profile")
        ) is not None
        assert user_profile_messages[0].fields["gender"] == 1
        assert user_profile_messages[0].fields["age"] == 33
        assert user_profile_messages[0].fields["weight"] == 80.1
        assert user_profile_messages[0].fields["friendly_name"] == "Fittie McFitface"


def test_monitoring_file(load_fit_file, data_dir):
    """NOTE: This file has accumulated fields"""
    fitfiles = decode(data_dir / "fittie_monitoring_file.fit")
    assert len(fitfiles) == 1
    for fitfile in fitfiles:
        assert fitfile.file_type == "monitoring_b"

        monitoring_messages = fitfile.get_messages_by_type("monitoring")

        assert len(monitoring_messages) == 24  # 24 hours

        for message in monitoring_messages:
            # Test if subfield has "scale" applied correctly
            assert message.fields["cycles"] * 2 == message.fields["steps"]


def test_chained_file(load_fit_file, data_dir):
    """NOTE: This file has accumulated fields"""
    fitfiles = decode(data_dir / "fittie_chained_file.fit")
    assert len(fitfiles) == 2

    for fitfile in fitfiles:
        # This is basically two times the 'minimal fit file'
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


@pytest.mark.parametrize("file_name", garmin_sdk_fitfile_names(), ids=garmin_sdk_fitfile_names())
def test_garmin_sdk_fitfile(file_name, data_dir):
    # Just check if we can decode them for now
    assert decode(data_dir / "from_garmin_sdk" / file_name)