"""Semantic checks for Garmin's published common file-type requirements.

Structural validity and CRCs are checked by decode. This separate, opt-in layer
checks File Id plus Activity, Course and Workout application conventions.
"""

from dataclasses import dataclass

from fittie.fitfile.heart_rate import seconds
from fittie.profile.fit_types import FIT_TYPES


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    message_index: int | None = None


def validate(file) -> list[ValidationIssue]:
    """Return all detected semantic issues; never alter decoded messages."""
    issues: list[ValidationIssue] = []
    groups = file.data_messages
    positions = {id(message): i for i, message in enumerate(file.messages)}

    def issue(code, text, message=None):
        issues.append(ValidationIssue(code, text, positions.get(id(message))))

    def require(message, names):
        for name in names:
            if message.fields.get(name) is None:
                issue("missing_field", f"Required field {name!r} is missing", message)

    def count(name, minimum=1, maximum=None):
        messages = groups.get(name, [])
        if len(messages) < minimum or (maximum is not None and len(messages) > maximum):
            issue(
                "message_count",
                f"{name}: expected {minimum}..{maximum if maximum is not None else 'many'} messages, got {len(messages)}",
            )
        return messages

    ids = count("file_id", 1, 1)
    if not ids:
        return issues
    first = ids[0]
    if not file.messages or file.messages[0] is not first:
        issue("message_order", "file_id must be the first data message", first)
    require(first, ("type", "manufacturer", "time_created"))
    file_type = first.fields.get("type")
    if isinstance(file_type, int):
        enum = FIT_TYPES["file"].values.get(file_type)
        file_type = enum.value_name if enum else file_type

    if file_type == "activity":
        activities = count("activity", 1, 1)
        sessions = count("session")
        laps = count("lap", len(sessions))
        records = count("record")
        for message in (*sessions, *laps, *groups.get("length", ())):
            require(
                message,
                ("start_time", "timestamp", "total_elapsed_time", "total_timer_time"),
            )
            start, end = (
                message.fields.get("start_time"),
                message.fields.get("timestamp"),
            )
            if start is not None and end is not None and seconds(end) < seconds(start):
                issue("time_order", "summary timestamp precedes start_time", message)
        for message in activities:
            require(message, ("num_sessions", "local_timestamp"))
            if message.fields.get("num_sessions") not in (None, len(sessions)):
                issue(
                    "session_count",
                    "activity.num_sessions does not match session messages",
                    message,
                )
        for message in records:
            require(message, ("timestamp",))
            if not any(
                key != "timestamp" and value is not None
                for key, value in message.fields.items()
            ):
                issue(
                    "missing_data",
                    "record needs a value in addition to timestamp",
                    message,
                )

    if file_type == "course":
        courses = count("course", 1, 1)
        count("lap")
        records = count("record")
        events = count("event", 2)
        for message in courses:
            require(message, ("name",))
        for message in groups.get("lap", ()):
            require(message, ("start_time", "timestamp"))
        for message in records:
            require(message, ("timestamp", "distance"))
        for message in groups.get("course_point", ()):
            require(message, ("timestamp",))
            if not any(
                key != "timestamp" and value is not None
                for key, value in message.fields.items()
            ):
                issue(
                    "missing_data",
                    "course_point needs a value in addition to timestamp",
                    message,
                )
        timers = []
        for message in events:
            if message.fields.get("event") in (0, "timer"):
                require(message, ("timestamp", "event_type"))
                timers.append(message)
        starts = [m for m in timers if m.fields.get("event_type") in (0, "start")]
        stops = [
            m for m in timers if m.fields.get("event_type") in (9, "stop_disable_all")
        ]
        if not starts or not stops:
            issue(
                "timer_events",
                "course requires timer start and stop_disable_all events",
            )
        if records:
            if starts and positions[id(starts[0])] > positions[id(records[0])]:
                issue(
                    "message_order",
                    "course timer start must precede records",
                    starts[0],
                )
            if stops and positions[id(stops[-1])] < positions[id(records[-1])]:
                issue(
                    "message_order", "course timer stop must follow records", stops[-1]
                )
        if (
            courses
            and records
            and positions[id(courses[0])] > positions[id(records[0])]
        ):
            issue("message_order", "course metadata must precede records", courses[0])

    if file_type == "workout" or groups.get("workout"):
        workouts = count("workout", 1, 1)
        steps = count("workout_step")
        for message in workouts:
            require(message, ("num_valid_steps",))
            if message.fields.get("num_valid_steps") not in (None, len(steps)):
                issue(
                    "step_count",
                    "workout.num_valid_steps does not match workout_step messages",
                    message,
                )
        for index, message in enumerate(steps):
            require(message, ("message_index", "duration_type", "duration_value"))
            duration = message.fields.get("duration_type")
            enum = (
                FIT_TYPES["wkt_step_duration"].values.get(duration)
                if isinstance(duration, int)
                else None
            )
            duration_name = enum.value_name if enum else duration
            # Repeat-until-last-lap steps imply the target and may omit target_type.
            if not isinstance(duration_name, str) or "last_lap" not in duration_name:
                require(message, ("target_type",))
            if message.fields.get("message_index") != index:
                issue(
                    "step_index",
                    "workout steps must have sequential zero-based indices",
                    message,
                )
            if isinstance(duration_name, str) and duration_name.startswith("repeat"):
                target = message.fields.get("duration_value")
                if isinstance(target, int) and not 0 <= target < index:
                    issue(
                        "repeat_target",
                        "repeat step must refer to an earlier step",
                        message,
                    )
            if workouts and positions[id(workouts[0])] > positions[id(message)]:
                issue("message_order", "workout metadata must precede steps", message)

    if file_type in ("course", "activity"):
        previous = None
        for message in groups.get("record", ()):
            timestamp = message.fields.get("timestamp")
            if timestamp is None:
                continue
            current = seconds(timestamp)
            if previous is not None and current < previous:
                issue("time_order", "record timestamps are not chronological", message)
            previous = current

    developers: set[int] = set()
    applications: dict = {}
    descriptions: set[tuple[int, int]] = set()
    for message in file.messages:
        if message.definition is None:
            continue
        number = message.definition.global_message_type
        if number == 207:
            require(message, ("developer_data_index",))
            index = message.fields.get("developer_data_index")
            if isinstance(index, int):
                application = message.fields.get("application_id")
                if (
                    applications.get(index) is not None
                    and applications[index] != application
                ):
                    descriptions = {key for key in descriptions if key[0] != index}
                applications[index] = application
                developers.add(index)
        elif number == 206:
            require(
                message,
                ("developer_data_index", "field_definition_number", "fit_base_type_id"),
            )
            index = message.fields.get("developer_data_index")
            num = message.fields.get("field_definition_number")
            if index not in developers:
                issue(
                    "developer_order",
                    "field_description precedes developer_data_id",
                    message,
                )
            if isinstance(index, int) and isinstance(num, int):
                descriptions.add((index, num))
        for key in message.developer_fields or ():
            if key not in descriptions:
                issue(
                    "developer_description",
                    f"developer field {key} lacks a preceding description",
                    message,
                )
    return issues
