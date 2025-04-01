from dataclasses import dataclass
from typing import Literal


@dataclass
class SubField:
    field_name: str
    field_type: str
    refs: list[dict[str, int | str] | None]
    array: Literal[False] | Literal["N"] | int | None = None
    components: str | list[str] | None = None
    scale: float | int | list[int] | None = None
    offset: int | None = None
    units: str | None = None
    bits: int | str | None = None
    accumulate: int | list[int] | None = None
    comment: str | None = None
    ref_field_name: str | list[str] | None = None
    ref_field_value: str | list[str] | None = None

    @property
    def is_array(self) -> bool:
        """Check whether the field is an array"""
        return self.array is not None

    @property
    def has_components(self) -> bool:
        """Check whether the field has components"""
        return self.components is not None


@dataclass
class FieldProfile:
    field_name: str
    field_type: str
    array: Literal[False] | Literal["N"] | int | None = None
    components: str | list[str] | None = None
    scale: float | int | list[int] | None = None
    offset: int | None = None
    units: str | None = None
    bits: int | str | None = None
    accumulate: int | list[int] | None = None
    subfields: list[SubField] | None = None
    comment: str | None = None

    @property
    def is_array(self) -> bool:
        """Check whether the field is an array"""
        return self.array is not None

    @property
    def has_components(self) -> bool:
        """Check whether the field has components"""
        return self.components is not None

    @property
    def has_subfields(self) -> bool:
        """Check whether the field has subfields"""
        if not self.subfields:
            return False
        return len(self.subfields) > 0


@dataclass
class MessageProfile:
    name: str
    fields: dict[int, FieldProfile]
    group: str | None
