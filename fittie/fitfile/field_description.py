from typing import Optional

from fittie.fitfile.profile.base_types import BaseType, BASE_TYPES


class FieldDescription:
    developer_data_index: int
    field_definition_number: int
    field_name: str
    base_type: BaseType
    native_message_number: Optional[int] = None
    native_field_number: Optional[int] = None
    units: Optional[str] = None

    def __init__(self, **kwargs):
        # Required fields
        self.developer_data_index = kwargs["developer_data_index"]
        self.field_definition_number = kwargs["field_definition_number"]
        self.field_name = kwargs["field_name"]
        self.base_type = BASE_TYPES[kwargs["fit_base_type_id"]]

        # Optional fields
        self.native_message_number = kwargs.get("native_mesg_num")
        self.native_field_number = kwargs.get("native_field_num")
        self.units = kwargs.get("units")

    def __str__(self) -> str:
        developer_index = f"{self.developer_data_index}_{self.field_definition_number}"
        return f"Field:{self.field_name=} {developer_index=}{self.units=}"

    def __repr__(self) -> str:
        return str(self)
