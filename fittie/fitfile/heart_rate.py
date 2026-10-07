"""Anchor HR event times and merge quarter-second samples into record intervals."""

from bisect import bisect_right
from datetime import datetime

from fittie.fitfile.processing import FIT_EPOCH


def seconds(timestamp):
    if isinstance(timestamp, datetime):
        if timestamp.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return (timestamp - FIT_EPOCH).total_seconds()
    return timestamp


def expand_heart_rates(messages: list[dict]) -> list[dict]:
    samples: list[dict] = []
    anchor = event_anchor = None
    for message in messages:
        events = message.get("event_timestamp")
        bpm = message.get("filtered_bpm")
        events = events if isinstance(events, list) else [events]
        bpm = bpm if isinstance(bpm, list) else [bpm]
        if len(events) != len(bpm):
            raise ValueError("HR timestamps and heart rates have different lengths")
        if message.get("timestamp") is not None:
            if len(events) != 1 or events[0] is None:
                raise ValueError("HR anchor requires exactly one valid event timestamp")
            anchor = seconds(message["timestamp"]) + (
                message.get("fractional_timestamp") or 0
            )
            event_anchor = events[0]
        if anchor is None or event_anchor is None:
            raise ValueError("HR data precedes its anchor timestamp")
        for event, rate in zip(events, bpm):
            if event is None or rate is None:
                continue
            # Expanded event_timestamp is in seconds; uint32 rolls at 2**22 s.
            delta = event - event_anchor
            if delta < 0:
                if -delta > 2**21:
                    delta += 2**22
                else:
                    raise ValueError("HR event timestamp precedes its anchor")
            time = anchor + delta
            if samples:
                previous = samples[-1]
                if time < previous["timestamp"]:
                    raise ValueError("HR samples are not in chronological order")
                for step in range(1, 21):
                    gap_time = previous["timestamp"] + step / 4
                    if gap_time >= time:
                        break
                    samples.append(
                        {"timestamp": gap_time, "heart_rate": previous["heart_rate"]}
                    )
            samples.append({"timestamp": time, "heart_rate": rate})
    return samples


def merge_heart_rates(hr_messages: list[dict], records: list[dict]) -> None:
    """Average samples in (previous record, current record], rounding half up.

    A duplicate record timestamp reuses the most recent consumed sample. Existing HR is kept
    where no sample is available, including after the last sample's interval.
    """
    if not hr_messages or not records:
        return
    samples = expand_heart_rates(hr_messages)
    times = [sample["timestamp"] for sample in samples]
    totals = [0]
    for sample in samples:
        totals.append(totals[-1] + sample["heart_rate"])
    previous = None
    previous_right = 0
    for record in records:
        if record.get("timestamp") is None:
            continue
        end = seconds(record["timestamp"])
        if previous is not None and end < previous:
            raise ValueError("record timestamps are not chronological")
        start = end - 1 if previous is None or previous == end else previous
        left, right = bisect_right(times, start), bisect_right(times, end)
        if previous == end:
            left = max(left, previous_right - 1)
        if right > left:
            record["heart_rate"] = int(
                (totals[right] - totals[left]) / (right - left) + 0.5
            )
        previous = end
        previous_right = right
