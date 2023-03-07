import pytest

from fittie.utils.gear_change_data import get_gear_change_data


@pytest.mark.parametrize(
    "data,expected",
    [
        (
            654380552,
            {
                "front_gear": 39,
                "front_gear_number": 1,
                "rear_gear": 14,
                "rear_gear_number": 8,
            },
        ),
        (
            654380041,
            {
                "front_gear": 39,
                "front_gear_number": 1,
                "rear_gear": 12,
                "rear_gear_number": 9,
            },
        ),
        (
            872549385,
            {
                "front_gear": 52,
                "front_gear_number": 2,
                "rear_gear": 12,
                "rear_gear_number": 9,
            },
        ),
        (
            0,
            {
                "front_gear": 0,
                "front_gear_number": 0,
                "rear_gear": 0,
                "rear_gear_number": 0,
            },
        ),
    ],
)
def test_get_gear_change_data(data, expected):
    assert get_gear_change_data(data) == expected
