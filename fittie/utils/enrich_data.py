from __future__ import annotations  # Added for type hints

from typing import Any

from fittie.fitfile.profile.fit_types import FIT_TYPES
from fittie.fitfile.util import datetime_from_timestamp


def enrich_data(fields: dict[str, Any]) -> None:
    """Modifies the field values in place with a lookup value from the FIT sdk"""
    for key, value in fields.items():
        if key == "timestamp":
            fields[key] = datetime_from_timestamp(value)
            continue

        if key in FIT_TYPES:
            try:
                fields[key] = FIT_TYPES[key].values[value].value_name
            except KeyError:
                ...
