import struct
from io import BytesIO

import pytest

from fittie import DecodeOptions, Encoder, decode, iter_files, iter_messages
from fittie.fitfile.heart_rate import expand_heart_rates, merge_heart_rates
from fittie.fitfile.utils.exceptions import DecodeException
from tests.fittie.fitfile.test_protocol import definition, fit_bytes


def test_raw_values_and_independent_expansion_options():
    writer = Encoder()
    writer.write("record", {"speed": 2.345, "altitude": 100})
    raw = (
        decode(
            BytesIO(writer.to_bytes()),
            options=DecodeOptions(apply_scale_and_offset=False),
        )[0]
        .messages[0]
        .fields
    )
    assert raw["speed"] == raw["enhanced_speed"] == 2345
    assert raw["altitude"] == raw["enhanced_altitude"] == 3000
    native = (
        decode(
            BytesIO(writer.to_bytes()), options=DecodeOptions(expand_components=False)
        )[0]
        .messages[0]
        .fields
    )
    assert native == {"speed": 2.345, "altitude": 100}
    writer = Encoder()
    writer.write("event", {"event": "battery", "data": 3500})
    assert (
        "battery_level"
        not in decode(
            BytesIO(writer.to_bytes()), options=DecodeOptions(expand_subfields=False)
        )[0]
        .messages[0]
        .fields
    )


def test_all_matching_subfield_aliases_are_exposed():
    writer = Encoder()
    writer.write(
        "workout_step", {"duration_type": 11, "target_type": 1, "target_value": 80}
    )
    fields = decode(BytesIO(writer.to_bytes()))[0].messages[0].fields
    assert fields["target_hr_zone"] == fields["repeat_hr"] == 80


def test_streaming_callbacks_order_and_caller_ownership():
    writer = Encoder()
    writer.write("record", {"heart_rate": 120})
    writer.write("event", {"event": "timer", "data": 0})
    writer.write("record", {"heart_rate": 121})
    seen = []
    source = BytesIO(writer.to_bytes() * 2)
    messages = list(
        iter_messages(source, message_listener=lambda n, f: seen.append((n, f)))
    )
    assert [n for n, _ in seen] == [20, 21, 20] * 2
    assert [m.fields for m in messages] == [f for _, f in seen]
    assert not source.closed
    assert len(list(iter_files(BytesIO(writer.to_bytes() * 2)))) == 2


def test_streaming_is_lazy_and_crc_is_checked_on_exhaustion():
    writer = Encoder()
    for rate in range(100, 110):
        writer.write("record", {"heart_rate": rate})
    data = bytearray(writer.to_bytes())
    data[-1] ^= 1
    source = BytesIO(data)
    iterator = iter_messages(source)
    assert source.tell() == 0
    assert next(iterator).fields["heart_rate"] == 100
    assert source.tell() < len(data) - 2
    with pytest.raises(DecodeException, match="crc"):
        list(iterator)
    assert not source.closed


def test_closing_stream_iterator_leaves_caller_stream_open():
    writer = Encoder()
    writer.write("record", {"heart_rate": 120})
    source = BytesIO(writer.to_bytes())
    iterator = iter_messages(source)
    next(iterator)
    iterator.close()
    assert not source.closed


def test_heart_rate_expansion_and_last_interval_merge():
    heart_rates = [
        {
            "timestamp": 100,
            "fractional_timestamp": 0.25,
            "event_timestamp": 1,
            "filtered_bpm": 100,
        },
        {"event_timestamp": [1.5, 2], "filtered_bpm": [120, 140]},
    ]
    assert expand_heart_rates(heart_rates) == [
        {"timestamp": 100.25, "heart_rate": 100},
        {"timestamp": 100.5, "heart_rate": 100},
        {"timestamp": 100.75, "heart_rate": 120},
        {"timestamp": 101.0, "heart_rate": 120},
        {"timestamp": 101.25, "heart_rate": 140},
    ]
    records = [
        {"timestamp": 101},
        {"timestamp": 102},
        {"timestamp": 103, "heart_rate": 80},
    ]
    merge_heart_rates(heart_rates, records)
    assert [r["heart_rate"] for r in records] == [110, 140, 80]


def test_duplicate_record_timestamp_reuses_last_sample():
    heart_rates = [
        {"timestamp": 100, "event_timestamp": 0, "filtered_bpm": 100},
        {"event_timestamp": 0.75, "filtered_bpm": 120},
    ]
    records = [{"timestamp": 101}, {"timestamp": 101}]
    merge_heart_rates(heart_rates, records)
    assert records[0]["heart_rate"] == 107
    assert records[1]["heart_rate"] == 120


def test_heart_rate_gaps_are_carried_for_at_most_five_seconds():
    expanded = expand_heart_rates(
        [
            {"timestamp": 100, "event_timestamp": 0, "filtered_bpm": 100},
            {"event_timestamp": 20, "filtered_bpm": 120},
        ]
    )
    assert len(expanded) == 22
    assert expanded[-2]["timestamp"] == 105
    assert expanded[-1]["timestamp"] == 120


def test_heart_rate_rollover():
    expanded = expand_heart_rates(
        [
            {"timestamp": 100, "event_timestamp": 2**22 - 0.5, "filtered_bpm": 100},
            {"event_timestamp": 0, "filtered_bpm": 120},
        ]
    )
    assert expanded[-1]["timestamp"] == 100.5


@pytest.mark.parametrize(
    "messages",
    [
        [{"event_timestamp": 1, "filtered_bpm": 100}],
        [{"timestamp": 100, "event_timestamp": [1, 2], "filtered_bpm": [100, 110]}],
        [{"timestamp": 100, "event_timestamp": 1, "filtered_bpm": [100, 110]}],
    ],
)
def test_bad_hr_anchors_and_arrays_are_rejected(messages):
    with pytest.raises(ValueError):
        expand_heart_rates(messages)


def test_incompatible_hr_options_fail_early():
    with pytest.raises(ValueError):
        DecodeOptions(merge_heart_rates=True, apply_scale_and_offset=False)
    with pytest.raises(ValueError):
        list(iter_messages(BytesIO(), options=DecodeOptions(merge_heart_rates=True)))


def test_unknown_native_base_type_preserves_bytes_and_next_record():
    payload = definition(0, 65281, [(1, 3, 31), (253, 4, 0x86)])
    payload += b"\0abc" + struct.pack("<I", 100) + b"\0def" + struct.pack("<I", 101)
    file = decode(BytesIO(fit_bytes(payload)))[0]
    assert file.get_messages_by_type("unknown_65281")[0].fields == {
        "unknown_65281_unknown_field_1": b"abc",
        "timestamp": 100,
    }
    assert file.messages[1].fields["timestamp"] == 101
    assert (
        decode(BytesIO(file.encode()))[0].messages[1].fields == file.messages[1].fields
    )


def test_uptime_timestamps_do_not_become_dates():
    writer = Encoder()
    writer.write("record", {"timestamp": 100})
    assert (
        decode(
            BytesIO(writer.to_bytes()),
            options=DecodeOptions(convert_datetimes_to_dates=True),
        )[0]
        .messages[0]
        .fields["timestamp"]
        == 100
    )


def test_nonseekable_stream_with_short_reads():
    writer = Encoder()
    writer.write("record", {"heart_rate": 120})

    class Fragmented:
        def __init__(self, data):
            self.stream = BytesIO(data)

        def read(self, size):
            return self.stream.read(min(size, 2))

    messages = list(iter_messages(Fragmented(writer.to_bytes())))
    assert messages[0].fields["heart_rate"] == 120


def test_future_base_type_for_accumulated_native_field_is_opaque():
    payload = definition(0, 20, [(5, 4, 31)]) + b"\0abcd"
    fields = decode(BytesIO(fit_bytes(payload)))[0].messages[0].fields
    assert fields["distance"] == b"abcd"


def test_available_fields_includes_old_definitions_and_expansions():
    writer = Encoder()
    writer.write("record", {"speed": 1.2})
    for i in range(20):
        writer.write("record", {"heart_rate": [100] * (i + 1)})
    file = decode(BytesIO(writer.to_bytes()))[0]
    assert file.available_fields["speed"] == "m/s"
    assert file.available_fields["enhanced_speed"] == "m/s"
    assert file.available_fields["heart_rate"] == "bpm"


def test_duplicate_native_definitions_are_rejected():
    with pytest.raises(DecodeException, match="duplicate native"):
        decode(BytesIO(fit_bytes(definition(0, 20, [(3, 1, 2), (3, 1, 2)]))))
