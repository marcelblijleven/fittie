from __future__ import annotations  # Added for type hints


def get_gear_change_data(data: int) -> dict[str, int]:
    """
    Reads rear gear number, rear gear, front gear number, front gear
    from the provided data.

    No check will be done to verify if the provided data is correct

    Each gear information is 8 bits long
    """
    gear_change_data = {
        "rear_gear_number": data & 255,
        "rear_gear": data >> 8 & 255,
        "front_gear_number": data >> 16 & 255,
        "front_gear": data >> 24 & 255,
    }

    return gear_change_data
