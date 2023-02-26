from datetime import datetime, timezone

from fittie.fitfile.util import rollover_timestamp, datetime_from_timestamp


def test_rollover_timestamp():
    """
    Test data from FIT file documentation
    """
    initial_timestamp = 0x0000003B

    assert (
        resultant_timestamp := rollover_timestamp(initial_timestamp, 0b11101)
    ) == 0x3D

    assert (
        resultant_timestamp := rollover_timestamp(resultant_timestamp, 0b00010)
    ) == 0x42

    assert (
        resultant_timestamp := rollover_timestamp(resultant_timestamp, 0b00101)
    ) == 0x45

    assert rollover_timestamp(resultant_timestamp, 0b00001) == 0x61


def test_datetime_from_timestamp():
    assert datetime_from_timestamp(1046114793) == datetime(
        2023, 2, 23, 19, 26, 33, tzinfo=timezone.utc
    )
    assert datetime_from_timestamp(1046119077) == datetime(
        2023, 2, 23, 20, 37, 57, tzinfo=timezone.utc
    )
