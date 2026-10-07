"""Independent binary examples for profile components and accumulating counters."""

import struct
from io import BytesIO

import pytest

from fittie import decode
from fittie.fitfile.components import get_profile_plan
from fittie.profile import FieldProfile, MessageProfile, SubField
from fittie.profile.messages import MESSAGES
from fittie.profile.util import get_message_profile
from tests.fittie.fitfile.test_protocol import definition, fit_bytes


def records(payload, group="record"):
    return [
        m.fields for m in decode(BytesIO(fit_bytes(payload)))[0].data_messages[group]
    ]


def packed(speed, distance):
    return (speed | (distance << 12)).to_bytes(3, "little")


def test_compressed_speed_distance_and_nested_enhanced_speed():
    payload = definition(0, 20, [(8, 3, 13)])
    payload += b"\x00" + packed(123, 4090)
    payload += b"\x00" + packed(234, 3)
    first, second = records(payload)
    assert first["speed"] == first["enhanced_speed"] == 1.23
    assert first["distance"] == 4090 / 16
    assert second["speed"] == second["enhanced_speed"] == 2.34
    assert second["distance"] == 4099 / 16
    assert first["compressed_speed_distance"] == list(packed(123, 4090))


def test_full_distance_seeds_counter_in_component_units():
    payload = definition(0, 20, [(5, 4, 0x86)]) + b"\x00" + struct.pack("<I", 100_000)
    payload += definition(1, 20, [(8, 3, 13)]) + b"\x01" + packed(0, 16001 & 4095)
    assert records(payload)[1]["distance"] == 1000.0625


def test_full_counters_reset_and_survive_local_definition_changes():
    payload = definition(0, 20, [(19, 4, 0x86)]) + b"\x00" + struct.pack("<I", 1000)
    payload += definition(1, 20, [(18, 1, 2)]) + b"\x01\xe9"  # 1001 mod 256
    payload += definition(1, 20, [(28, 2, 0x84)]) + b"\x01\xfe\xff"
    payload += b"\x01\x01\x00"  # power rollover
    payload += definition(0, 20, [(19, 4, 0x86)]) + b"\x00" + struct.pack("<I", 10)
    payload += definition(1, 20, [(18, 1, 2)]) + b"\x01\x0b"
    values = records(payload)
    assert values[1]["total_cycles"] == 1001
    assert values[3]["accumulated_power"] == 65537
    assert values[-1]["total_cycles"] == 11


def test_accumulators_reset_for_each_member_and_decode_call():
    payload = definition(0, 20, [(18, 1, 2)]) + b"\x00\xfe\x00\x01"
    member = fit_bytes(payload)
    for _ in range(2):
        result = decode(BytesIO(member * 2))
        assert [
            [m.fields["total_cycles"] for m in f.data_messages["record"]]
            for f in result
        ] == [[254, 257], [254, 257]]


def test_invalid_containers_do_not_advance_accumulators():
    payload = definition(0, 20, [(18, 1, 2)]) + b"\x00\xfe\x00\xff\x00\x01"
    first, invalid, last = records(payload)
    assert first["total_cycles"] == 254
    assert "total_cycles" not in invalid
    assert last["total_cycles"] == 257


@pytest.mark.parametrize("big", [False, True])
def test_gear_components_and_inactive_subfields(big):
    payload = definition(0, 21, [(3, 4, 0x86), (0, 1, 0)], big_endian=big)
    for event in (42, 43, 0):
        payload += (
            b"\x00" + struct.pack(">I" if big else "<I", 0x3422020B) + bytes([event])
        )
    messages = records(payload, "event")
    for message in messages[:2]:
        assert message["rear_gear_num"] == 11
        assert message["rear_gear"] == 2
        assert message["front_gear_num"] == 34
        assert message["front_gear"] == 52
    assert "rear_gear" not in messages[2]


def test_expanded_field_can_select_a_subfield():
    # cycles precedes the component that supplies its activity_type reference.
    payload = definition(0, 55, [(3, 4, 0x86), (24, 1, 13)])
    message = records(
        payload + b"\x00" + struct.pack("<I", 123) + bytes([6 | (3 << 5)]), "monitoring"
    )[0]
    assert message["activity_type"] == 6
    assert message["intensity"] == 3
    assert message["cycles"] == 61.5
    assert message["steps"] == 123


def test_hr_repeated_components_append_after_full_timestamp_array():
    payload = definition(0, 132, [(9, 8, 0x86), (10, 5, 13)])
    bits = 4094 | (3 << 12) | (8 << 24)
    message = records(
        payload + b"\x00" + struct.pack("<II", 4089, 4090) + bits.to_bytes(5, "little"),
        "hr",
    )[0]
    assert message["event_timestamp"] == [
        v / 1024 for v in (4089, 4090, 4094, 4099, 4104)
    ]


@pytest.mark.parametrize("big", [False, True])
def test_components_span_numeric_array_elements(big):
    payload = definition(0, 372, [(1, 4, 0x84)], big_endian=big)
    message = records(
        payload
        + b"\x00"
        + struct.pack(">HH" if big else "<HH", 123 | (1 << 14), 456 | (1 << 15)),
        "raw_bbi",
    )[0]
    assert message["time"] == [123, 456]
    assert message["quality"] == [1, 0]
    assert message["gap"] == [0, 1]


def test_short_component_container_stops_without_inventing_values():
    payload = definition(0, 20, [(8, 2, 13)]) + b"\x00\x64\x00"
    message = records(payload)[0]
    assert message["speed"] == message["enhanced_speed"] == 1
    assert "distance" not in message


def test_byte_arrays_preserve_ff_when_not_wholly_invalid():
    payload = definition(0, 80, [(2, 3, 13)]) + b"\x00\x00\xff\x01"
    message = records(payload, "ant_rx")[0]
    assert message["mesg_data"] == [0, 255, 1]
    assert message["data"] == [255, 1]


def test_expansion_uses_component_scale_and_offset_once():
    payload = definition(0, 20, [(2, 2, 0x84)]) + b"\x00" + struct.pack("<H", 3000)
    message = records(payload)[0]
    assert message["altitude"] == message["enhanced_altitude"] == 100


def test_native_scalar_preserves_precision_when_component_also_present():
    payload = (
        definition(0, 20, [(73, 4, 0x86), (6, 2, 0x84)])
        + b"\x00"
        + struct.pack("<IH", 12345, 10000)
    )
    assert records(payload)[0]["enhanced_speed"] == 12.345
    assert records(payload)[0]["speed"] == 10


def test_large_full_counter_does_not_round_through_float():
    value = 2**53 + 1
    payload = definition(0, 20, [(29, 8, 0x8F)]) + b"\x00" + struct.pack("<Q", value)
    payload += definition(1, 20, [(28, 2, 0x84)]) + b"\x01\x02\x00"
    assert records(payload)[1]["accumulated_power"] == value + 1


@pytest.fixture
def custom_profile(monkeypatch):
    def install(fields):
        monkeypatch.setitem(MESSAGES, 65282, MessageProfile("custom", fields, None))
        get_message_profile.cache_clear()
        get_profile_plan.cache_clear()

    yield install
    get_message_profile.cache_clear()
    get_profile_plan.cache_clear()


def test_signed_components(custom_profile):
    custom_profile(
        {
            0: FieldProfile("packed", "uint16", components="signed", bits=8),
            1: FieldProfile("signed", "sint16"),
        }
    )
    payload = definition(0, 65282, [(0, 2, 0x84)]) + b"\x00\xff\x00"
    assert records(payload, "unknown_65282")[0]["signed"] == -1


def test_repeated_invalid_components_preserve_positions(custom_profile):
    custom_profile(
        {
            0: FieldProfile(
                "packed", "uint32", components=["value", "value"], bits="8,8"
            ),
            1: FieldProfile("value", "uint8", array="N"),
        }
    )
    payload = definition(0, 65282, [(0, 4, 0x86)]) + b"\x00\xff\x01\x00\x00"
    assert records(payload, "unknown_65282")[0]["value"] == [None, 1]


def test_accumulators_are_isolated_by_global_message(custom_profile):
    custom_profile(
        {
            0: FieldProfile(
                "cycles", "uint8", components="total_cycles", bits=8, accumulate=1
            ),
            1: FieldProfile("total_cycles", "uint32"),
        }
    )
    payload = definition(0, 20, [(18, 1, 2)]) + b"\x00\xfe"
    payload += definition(1, 65282, [(0, 1, 2)]) + b"\x01\x01"
    payload += b"\x00\x01"
    result = decode(BytesIO(fit_bytes(payload)))[0]
    assert result.data_messages["unknown_65282"][0].fields["total_cycles"] == 1
    assert result.data_messages["record"][-1].fields["total_cycles"] == 257


def test_nested_subfield_components(custom_profile):
    custom_profile(
        {
            0: FieldProfile("packed", "uint16", components="data", bits=16),
            1: FieldProfile(
                "data",
                "uint16",
                subfields=[
                    SubField(
                        "selected",
                        "uint16",
                        [{"field_name": "kind", "value_number": 0}],
                        components="value",
                        bits=8,
                    )
                ],
            ),
            2: FieldProfile("kind", "enum"),
            3: FieldProfile("value", "uint8"),
        }
    )
    payload = definition(0, 65282, [(0, 2, 0x84), (2, 1, 0)]) + b"\x00\x2a\x00\x00"
    assert records(payload, "unknown_65282")[0]["value"] == 42


def test_nested_component_conversion_does_not_truncate_float_roundoff():
    payload = definition(0, 20, [(8, 3, 13)]) + b"\x00" + packed(201, 0)
    message = records(payload)[0]
    assert message["speed"] == message["enhanced_speed"] == 2.01


def test_independent_accumulators_in_one_container(custom_profile):
    custom_profile(
        {
            0: FieldProfile(
                "packed", "uint8", components=["a", "b"], bits="4,4", accumulate=[1, 1]
            ),
            1: FieldProfile("a", "uint32"),
            2: FieldProfile("b", "uint32"),
        }
    )
    values = records(
        definition(0, 65282, [(0, 1, 2)]) + b"\x00\xe8\x00\x19", "unknown_65282"
    )
    assert [(m["a"], m["b"]) for m in values] == [(8, 14), (9, 17)]


def test_invalid_full_counter_does_not_reset_state():
    payload = definition(0, 20, [(18, 1, 2)]) + b"\x00\xfe"
    payload += definition(1, 20, [(19, 4, 0x86)]) + b"\x01\xff\xff\xff\xff"
    payload += b"\x00\x01"
    assert records(payload)[-1]["total_cycles"] == 257


@pytest.mark.parametrize("full_first", [False, True])
def test_full_distance_in_same_message_is_authoritative(full_first):
    field_defs = [(5, 4, 0x86), (8, 3, 13)]
    values = [struct.pack("<I", 100000), packed(123, 16000 & 4095)]
    if not full_first:
        field_defs.reverse()
        values.reverse()
    payload = definition(0, 20, field_defs) + b"\x00" + b"".join(values)
    payload += definition(1, 20, [(8, 3, 13)]) + b"\x01" + packed(123, 16001 & 4095)
    first, second = records(payload)
    assert first["distance"] == 1000
    assert second["distance"] == 1000.0625


def test_zero_native_scalar_is_preserved():
    payload = (
        definition(0, 20, [(73, 4, 0x86), (6, 2, 0x84)])
        + b"\x00"
        + struct.pack("<IH", 0, 10000)
    )
    assert records(payload)[0]["enhanced_speed"] == 0


def test_components_with_compressed_timestamp_header():
    payload = definition(0, 20, [(253, 4, 0x86), (18, 1, 2)])
    payload += b"\x00" + struct.pack("<I", 100) + b"\xfe\x85\x01"
    first, second = records(payload)
    assert first["timestamp"] == 100
    assert second["timestamp"] == 101
    assert second["total_cycles"] == 257


@pytest.mark.parametrize("base,fmt", [(0x88, "f"), (0x89, "d")])
@pytest.mark.parametrize("big", [False, True])
def test_compiled_float_arrays_preserve_invalid_and_other_nan_values(base, fmt, big):
    import math

    size = struct.calcsize(fmt)
    endian = ">" if big else "<"
    payload = definition(0, 20, [(200, size * 3, base)], big_endian=big)
    payload += (
        b"\x00"
        + struct.pack(endian + fmt, 1.25)
        + b"\xff" * size
        + struct.pack(endian + fmt, float("nan"))
    )
    values = records(payload)[0]["record_unknown_field_200"]
    assert values[:2] == [1.25, None]
    assert math.isnan(values[2])


def test_utf8_string_components_ignore_scale_and_offset(custom_profile):
    custom_profile(
        {
            0: FieldProfile(
                "packed",
                "byte",
                array=3,
                components=["label", "label", "label"],
                bits="8,8,8",
                scale=[2, 3, 4],
                offset=10,
            ),
            1: FieldProfile("label", "string"),
        }
    )
    payload = definition(0, 65282, [(0, 3, 13)]) + b"\x00\xc3\xa9\x00"
    assert records(payload, "unknown_65282")[0]["label"] == "é"


def test_encoding_native_array_plus_derived_values_does_not_duplicate(custom_profile):
    from fittie import encode

    custom_profile(
        {
            0: FieldProfile(
                "packed", "uint16", components=["target", "target"], bits="8,8"
            ),
            1: FieldProfile("target", "uint16", array="N"),
        }
    )
    payload = definition(0, 65282, [(0, 2, 0x84), (1, 2, 0x84)]) + b"\0\x01\x02\x05\0"
    original = decode(BytesIO(fit_bytes(payload)))
    assert original[0].messages[0].fields["target"] == [5, 1, 2]
    again = decode(BytesIO(encode(original)))
    assert again[0].messages[0].fields["target"] == [5, 1, 2]
