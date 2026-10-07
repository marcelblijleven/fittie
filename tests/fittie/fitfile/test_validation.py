from io import BytesIO

import pytest

from fittie import Encoder, decode, validate


def identity(writer, kind):
    writer.write("file_id", {"type": kind, "manufacturer": 1, "time_created": 100})


def test_valid_workout_and_invalid_step_reference():
    writer = Encoder()
    identity(writer, "workout")
    writer.write("workout", {"num_valid_steps": 2})
    writer.write(
        "workout_step",
        {
            "message_index": 0,
            "duration_type": "time",
            "duration_value": 60000,
            "target_type": "open",
        },
    )
    writer.write(
        "workout_step",
        {
            "message_index": 1,
            "duration_type": "repeat_until_steps_cmplt",
            "duration_value": 0,
            "target_type": "open",
            "target_value": 3,
        },
    )
    file = decode(BytesIO(writer.to_bytes()))[0]
    assert file.validate() == []
    file.messages[-1].fields["duration_value"] = 2
    assert [issue.code for issue in validate(file)] == ["repeat_target"]


def test_activity_requires_summaries_and_record_data():
    writer = Encoder()
    identity(writer, "activity")
    writer.write("record", {"timestamp": 100})
    file = decode(BytesIO(writer.to_bytes()))[0]
    issues = validate(file)
    assert any(issue.code == "missing_data" for issue in issues)
    assert any("session" in issue.message for issue in issues)
    assert any("activity" in issue.message for issue in issues)


def test_valid_activity():
    writer = Encoder()
    identity(writer, "activity")
    writer.write("record", {"timestamp": 100, "heart_rate": 120})
    for kind in ["lap", "session"]:
        writer.write(
            kind,
            {
                "start_time": 100,
                "timestamp": 101,
                "total_elapsed_time": 1,
                "total_timer_time": 1,
            },
        )
    writer.write("activity", {"num_sessions": 1, "local_timestamp": 101})
    assert validate(decode(BytesIO(writer.to_bytes()))[0]) == []


def test_valid_course_and_missing_timer():
    writer = Encoder()
    identity(writer, "course")
    writer.write("course", {"name": "Example"})
    writer.write("lap", {"start_time": 100, "timestamp": 101})
    writer.write("event", {"timestamp": 100, "event": "timer", "event_type": "start"})
    writer.write("record", {"timestamp": 100, "distance": 0})
    writer.write("record", {"timestamp": 101, "distance": 1})
    writer.write(
        "event", {"timestamp": 101, "event": "timer", "event_type": "stop_disable_all"}
    )
    file = decode(BytesIO(writer.to_bytes()))[0]
    assert validate(file) == []
    file.data_messages["event"].pop()
    assert any(issue.code == "timer_events" for issue in validate(file))


@pytest.mark.parametrize("kind", ["settings", "sport", "monitoring_a", "weight"])
def test_other_file_types_use_common_requirements(kind):
    writer = Encoder()
    identity(writer, kind)
    assert validate(decode(BytesIO(writer.to_bytes()))[0]) == []


def test_missing_file_id_is_reported():
    assert validate(decode(BytesIO(Encoder().to_bytes()))[0])[0].code == "message_count"
