"""Encoding tests use independently described binary values and round trips."""

import struct
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest

from fittie import DecodeOptions, Encoder, decode, encode
from fittie.fitfile.field_definitions import FieldDefinition
from fittie.profile.base_types import BASE_TYPES
from tests.fittie.fitfile.test_protocol import definition, fit_bytes


@pytest.mark.parametrize("base", list(BASE_TYPES))
@pytest.mark.parametrize("endian", ["<", ">"])
def test_encode_all_base_types_arrays_and_invalids(base, endian):
    kind = BASE_TYPES[base]
    if kind.value_type is str:
        value, size = ["é", "two"], 7
    elif kind.name == "byte":
        value, size = [0, 255, 7], 3
    elif kind.value_type is float:
        value, size = [1.25, None, -2.5], kind.size * 3
    else:
        value, size = [1, None, 3], kind.size * 3
    encoder = Encoder()
    encoder.write(
        65281,
        {1: value},
        field_definitions=[FieldDefinition(1, size, kind)],
        endianness=endian,
    )
    result = decode(BytesIO(encoder.to_bytes()))[0].messages[0]
    assert result.fields["unknown_65281_unknown_field_1"] == value
    if kind.value_type is float:
        assert b"\xff" * kind.size in encoder.to_bytes()


def test_profile_names_scales_dates_and_subfields():
    writer = Encoder()
    date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    writer.write(
        "file_id", {"type": "activity", "manufacturer": "garmin", "time_created": date}
    )
    writer.write(
        "record",
        {"timestamp": date, "altitude": 100.2, "speed": 2.345, "heart_rate": 120},
    )
    writer.write("event", {"event": "battery", "battery_level": 3.5})
    file = decode(BytesIO(writer.to_bytes()))[0]
    assert file.messages[1].fields["speed"] == 2.345
    assert file.messages[1].fields["altitude"] == pytest.approx(100.2)
    assert file.messages[2].fields["data"] == 3500
    assert file.messages[2].fields["battery_level"] == 3.5
    assert file.file_id["time_created"] == date
    converted = decode(
        BytesIO(writer.to_bytes()),
        options=DecodeOptions(
            convert_types_to_strings=True, convert_datetimes_to_dates=True
        ),
    )[0]
    assert converted.file_type == "activity"
    assert converted.messages[1].fields["timestamp"] == date
    assert converted.messages[2].fields["event"] == "battery"
    assert (
        decode(BytesIO(encode(converted)))[0].messages[2].fields["battery_level"] == 3.5
    )


def test_all_16_local_slots_can_be_reused_without_losing_order():
    writer = Encoder()
    field = [FieldDefinition(1, 1, BASE_TYPES[2])]
    for repeat in range(2):
        for number in range(65280, 65300):
            writer.write(number, {1: repeat + 1}, field_definitions=field)
    file = decode(BytesIO(writer.to_bytes()))[0]
    assert len(file.messages) == 40
    assert [m.definition.global_message_type for m in file.messages] == list(
        range(65280, 65300)
    ) * 2
    assert [m.fields for m in decode(BytesIO(encode(file)))[0].messages] == [
        m.fields for m in file.messages
    ]


def test_definitions_are_reused_for_same_shape():
    writer = Encoder()
    writer.write("record", {"heart_rate": 120})
    size = len(writer.to_bytes())
    writer.write("record", {"heart_rate": 121})
    assert len(writer.to_bytes()) - size == 2
    assert writer.to_bytes() == writer.finish()


@pytest.mark.parametrize(
    "fields",
    [
        {"heart_rate": 256},
        {"unknown": 1},
        {"timestamp": datetime(2025, 1, 1)},
        {"speed": [1.0] * 128},
    ],
)
def test_invalid_encoding_does_not_mutate_writer(fields):
    writer = Encoder()
    original = writer.to_bytes()
    with pytest.raises(ValueError):
        writer.write("record", fields)
    assert writer.to_bytes() == original


def test_bad_subfield_selector_is_rejected():
    writer = Encoder()
    with pytest.raises(ValueError, match="reference"):
        writer.write("event", {"event": "timer", "battery_level": 3.5})


def test_compressed_timestamp_can_be_written_as_normal_message():
    payload = definition(0, 20, [(253, 4, 0x86), (3, 1, 2)])
    payload += b"\0" + struct.pack("<IB", 31, 120) + b"\x80\x79"
    original = decode(BytesIO(fit_bytes(payload)))
    again = decode(BytesIO(encode(original)))
    assert [m.fields for m in again[0].messages] == [
        m.fields for m in original[0].messages
    ]


def test_chained_encode_and_caller_owned_destination():
    writer = Encoder()
    writer.write("file_id", {"type": "settings"})
    members = decode(BytesIO(writer.to_bytes() * 3))
    destination = BytesIO()
    assert encode(members, destination) == destination.getvalue()
    assert not destination.closed
    assert len(decode(BytesIO(destination.getvalue()))) == 3


@pytest.mark.parametrize(
    "fixture",
    sorted((Path(__file__).parents[2] / "data").glob("*.fit")),
    ids=lambda p: p.name,
)
def test_committed_fixtures_roundtrip_every_field(fixture):
    original = decode(fixture)
    again = decode(BytesIO(encode(original)))
    assert [[m.fields for m in file.messages] for file in again] == [
        [m.fields for m in file.messages] for file in original
    ]
