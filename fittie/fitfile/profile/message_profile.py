from __future__ import annotations  # added for type hints

from dataclasses import dataclass
from typing import Union, Optional


@dataclass
class MessageProfile:
    @dataclass
    class FieldProfile:
        field_name: str
        field_type: str
        array: Optional[Union[bool, str, int]] = None
        components: Optional[Union[str, list[str]]] = None
        scale: Optional[Union[int, list[int]]] = None
        offset: Optional[int] = None
        units: Optional[str] = None
        bits: Optional[Union[int, str]] = None
        accumulate: Optional[Union[int, list[int]]] = None
        ref_field_name: Optional[Union[str, list[str]]] = None
        ref_field_value: Optional[Union[str, list[str]]] = None
        comment: Optional[str] = None

        @property
        def is_array(self) -> bool:
            """Check whether the field is an array"""
            return self.array is not None

        @property
        def has_components(self) -> bool:
            """Check whether the field has components"""
            return self.components is not None

    name: str
    fields: dict[int, FieldProfile]
    group: str
