from __future__ import annotations

from datetime import datetime, timezone

FIT_EPOCH = 631065600


def rollover_timestamp(previous_timestamp: int, offset: int) -> int:
    """
    Apply the compressed timestamp offset to the previous timestamp

    The offset is a 5-bit offset which rolls over every 32 seconds
    (0b11111 == 31). This means that consecutive compressed timestamps may
    never be more than 32 seconds apart

    The actual timestamp is calculated by concatenating the most significant 27 bits
    of the previous timestamp value and the 5 bit value of the offset field
    """
    max_length = 0b1111  # 0x0000001F

    if offset >= previous_timestamp & max_length:
        # Offset value is greater than least significant 5 bits of previous timestamp
        timestamp = (previous_timestamp & 0xFFFFFFE0) + offset
    else:
        # Offset is less than least significant 5 bits of previous timestamp
        timestamp = (previous_timestamp & 0xFFFFFFE0) + offset + 0x20

    return timestamp


def datetime_from_timestamp(timestamp: int) -> datetime:
    """
    Create a datetime from a timestamp using the Garmin FIT epoch, in UTC.
    """
    dt = datetime.utcfromtimestamp(timestamp + FIT_EPOCH)
    dt = dt.replace(tzinfo=timezone.utc)
    return dt
