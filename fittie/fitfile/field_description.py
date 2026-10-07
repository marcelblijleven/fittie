from fittie.profile.base_types import BASE_TYPES, BaseType


class FieldDescription:
    developer_data_index: int
    field_definition_number: int
    field_name: str
    base_type: BaseType | None
    native_message_number: int | None = None
    native_field_number: int | None = None
    units: str | None = None

    def __init__(self, **kwargs):
        # Required fields
        self.developer_data_index = kwargs["developer_data_index"]
        self.field_definition_number = kwargs["field_definition_number"]
        self.metadata = dict(kwargs)
        self.field_name = (
            kwargs.get("field_name")
            or f"developer_{self.developer_data_index}_{self.field_definition_number}"
        )
        if isinstance(self.field_name, list):
            self.field_name = self.field_name[0]
        self.fit_base_type_id = kwargs.get("fit_base_type_id")
        self.base_type = (
            BASE_TYPES.get(self.fit_base_type_id)
            if isinstance(self.fit_base_type_id, int)
            else None
        )
        if self.base_type is None and isinstance(self.fit_base_type_id, int):
            self.base_type = next(
                (
                    base
                    for base in BASE_TYPES.values()
                    if base.number == self.fit_base_type_id & 0x1F
                ),
                None,
            )

        # Optional fields
        self.native_message_number = kwargs.get("native_mesg_num")
        self.native_field_number = kwargs.get("native_field_num")
        self.units = kwargs.get("units")

    def __str__(self) -> str:
        developer_index = f"{self.developer_data_index}_{self.field_definition_number}"
        return f"Field:{self.field_name=} {developer_index=}{self.units=}"

    def __repr__(self) -> str:
        return str(self)
