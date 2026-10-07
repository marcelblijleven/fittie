from dataclasses import dataclass


@dataclass
class FieldTypeValue:
    value_name: str
    comment: str | None


@dataclass
class FieldType:
    base_type: str
    values: dict[int, FieldTypeValue]
