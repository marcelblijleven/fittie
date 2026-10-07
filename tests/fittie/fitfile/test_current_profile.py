"""Binary examples for definitions introduced by the profile refresh."""

import struct
from io import BytesIO

import pytest

from fittie import decode
from fittie.fitfile.components import get_profile_plan
from fittie.profile.messages import MESSAGES
from tests.fittie.fitfile.test_protocol import definition, fit_bytes


@pytest.mark.parametrize(
    "num,name,field,base,fmt,raw,key,expected",
    [
        (13, "training_settings", 153, 0x86, "I", 3500000, "precise_target_speed", 3.5),
        (104, "battery", 2, 2, "B", 75, "capacity", 75),
        (412, "nap_event", 1, 0x83, "h", -60, "start_timezone_offset", -60),
        (470, "sleep_disruption_severity_period", 0, 0, "B", 1, "severity", 1),
        (471, "sleep_disruption_overnight_severity", 0, 0, "B", 2, "severity", 2),
    ],
)
def test_new_message_fields(num, name, field, base, fmt, raw, key, expected):
    payload = definition(0, num, [(field, struct.calcsize(fmt), base)])
    payload += b"\x00" + struct.pack("<" + fmt, raw)
    decoded = decode(BytesIO(fit_bytes(payload)))[0]
    assert decoded.get_messages_by_type(name)[0].fields[key] == expected


def test_fieldless_padding_message():
    decoded = decode(BytesIO(fit_bytes(definition(0, 105, []) + b"\x00")))[0]
    assert decoded.get_messages_by_type("pad")[0].fields == {}


@pytest.mark.parametrize("num,sport,cadence", [(312, 11, 29), (313, 1, 14)])
def test_new_split_subfield_resolves_its_own_sport_selector(num, sport, cadence):
    payload = definition(0, num, [(cadence, 2, 0x84), (sport, 1, 0)])
    payload += b"\x00" + struct.pack("<HB", 128 * 90, 1)
    decoded = decode(BytesIO(fit_bytes(payload)))[0]
    fields = decoded.get_messages_by_type(MESSAGES[num].name)[0].fields
    assert fields["avg_running_cadence"] == 90


def test_all_bundled_component_and_subfield_plans_compile():
    for num in MESSAGES:
        get_profile_plan(num)
