from __future__ import annotations
import struct
from abc import ABC
from typing import BinaryIO, Optional
from uuid import UUID

BIG_ENDIAN = ">"
LITTLE_ENDIAN = "<"


class DataRecord(ABC):
    ...


class RecordHeader:
    """
    A one byte header to determine of the record is either a DefinitionMessage,
    Normal Data Message or a Compressed Timestamp Data Message

    Normal header
    - Bit 0-3, Value 0-15: Local message type
    - Bit 4, Value 0: Reserved
    - Bit 5, Value 0 or 1: Message Type Specific (e.g. Developer Data Flag)
    - Bit 6, Value 0 or 1: Message Type, 1: Definition Message, 0: Data Message
    - Bit 7, Value 0, Header type: Normal header

    Compressed timestamp header
    - Bit 0-4, Value 0-31, Time offset
    - Bit 5-6, Value 0-3: Local Message Type
    - Bit 7, Value 1: Compressed timestamp header
    """

    is_definition_message: bool
    is_developer_data: bool
    local_message_type: int
    time_offset: Optional[int]

    def __init__(
        self,
        is_definition_message: bool,
        is_developer_data: bool,
        local_message_type: int,
        time_offset: Optional[int] = None,
    ):
        self.is_definition_message = is_definition_message
        self.is_developer_data = is_developer_data
        self.local_message_type = local_message_type
        self.time_offset = time_offset

    @classmethod
    def from_data(cls, data: BinaryIO) -> RecordHeader:
        (value,) = struct.unpack("B", data.read(1))

        # Use a bit mask to get bit 7 to determine if this is a normal (0) or
        # compressed timestamp header (1)
        if is_timestamp := bool(value >> 7):
            is_definition_message = False
            is_developer_data = False

            # Shift 5 places to the right to get bits 7, 6 and 5
            # then apply mask 0b011 to get bits 6 and 5
            local_message_type = (value >> 5) & 0b011

            # Apply mask 0b11111 to get bit 4, 3, 2, 1 and 0
            time_offset = value & 0b111111
        else:
            # Apply mask 0b1000000 to get bit 6 to determine if the message
            # is a definition message
            is_definition_message = bool(value & 0b1000000)

            # Apply mask 0b100000 to determine if message contains developer data
            is_developer_data = bool(value & 0b100000)

            # Bit 4 is reserved and always 0, extra validity check
            if bool(value & 0b10000):
                raise ValueError("invalid byte received for RecordHeader")

            # Apply mask 0b1111 to get bit 3, 2, 1, and 0
            local_message_type = value & 0b1111
            time_offset = None

        return cls(
            is_definition_message,
            is_developer_data,
            local_message_type,
            time_offset,
        )

    decode = from_data


class FieldDefinition:
    """
    Specifies which FIT fields are included in the upcoming data message

    Byte 0 Field Definition Number
    Byte 1 Size
    Byte 2 Base Type
    """

    number: int
    size: int
    base_type: int

    def __init__(self, number: int, size: int, base_type: int):
        self.number = number
        self.size = size
        self.base_type = base_type

    @classmethod
    def from_data(cls, data: BinaryIO) -> FieldDefinition:
        number, size, base_type = struct.unpack("3B", data.read(3))

        if number == 255:
            raise ValueError(f"invalid field definition number received: {number}")

        return cls(number, size, base_type)

    decode = from_data


class DeveloperFieldDefinition:
    """
    Specifies Developer Data Fields which are used to map data within a DataMessage
    to the appropriate meta-data

    Byte 0 Field Number
    Byte 1 Size
    Byte 2 Developer Data Index
    """

    number: int
    size: int
    data_index: int

    def __init__(self, number: int, size: int, data_index: int):
        self.number = number
        self.size = size
        self.data_index = data_index

    @classmethod
    def from_data(cls, data: BinaryIO) -> DeveloperFieldDefinition:
        number, size, data_index = struct.unpack("3B", data.read(3))
        return cls(number, size, data_index)

    decode = from_data


class DefinitionMessage(DataRecord):
    """
    Defines a local message type and associates it to a specific FIT message,
    and then designate the byte alignment and field contents of the
    upcoming data message.

    Definition messages have a fixed content of 5 bytes, and a variable content part
    which contains the field definitions (3 bytes per field)

    Fixed content:
    - Reserved: 1 Byte
    - Architecture: 1 Byte
    - Global message number: 2 bytes
    - Number of fields: 1 byte
    """

    header: RecordHeader
    endianness: str
    global_message_type: int
    number_of_fields: int
    field_definitions: list[FieldDefinition]
    number_of_developer_fields: int
    developer_field_definitions: list[DeveloperFieldDefinition]

    def __init__(
        self,
        header: RecordHeader,
        endianness: str,
        global_message_type: int,
        field_definitions: list[FieldDefinition],
        developer_field_definitions: Optional[list[FieldDefinition]] = None,
    ):
        self.header = header
        self.endianness = endianness
        self.global_message_type = global_message_type
        self.number_of_fields = len(field_definitions)
        self.field_definitions = field_definitions

        if developer_field_definitions is None:
            developer_field_definitions = []

        self.number_of_developer_fields = len(developer_field_definitions)
        self.developer_field_definitions = developer_field_definitions

    @classmethod
    def from_data(cls, header: RecordHeader, data: BinaryIO) -> DefinitionMessage:
        if not header.is_definition_message:
            raise ValueError(
                "received non definition message header in DefinitionMessage"
            )

        (reserved,) = struct.unpack("B", data.read(1))

        if bool(reserved):
            raise ValueError("invalid data received for DefinitionMessage")

        (architecture,) = struct.unpack("B", data.read(1))

        endianness = BIG_ENDIAN if architecture else LITTLE_ENDIAN

        (global_message_type,) = struct.unpack(f"{endianness}H", data.read(2))
        (number_of_fields,) = struct.unpack("B", data.read(1))

        field_definitions: list[FieldDefinition] = []
        developer_field_definitions: Optional[list[FieldDefinition]] = None

        for field in range(number_of_fields):
            field_definitions.append(FieldDefinition.from_data(data))

        if header.is_developer_data:
            developer_field_definitions = []
            (number_of_developer_fields,) = struct.unpack("B", data.read(1))

            for field in range(number_of_developer_fields):
                developer_field_definitions.append(FieldDefinition.from_data(data))

        return cls(
            header,
            endianness,
            global_message_type,
            field_definitions,
            developer_field_definitions,
        )

    decode = from_data


class DataMessage(DataRecord):
    """
    Contains a local message type and populated data fields as described by the
    preceding definition message.

    There are two types of data message:
        Normal Data Message
        Compressed Timestamp Data Message

    Related DefinitionMessages and DataMessages share a local message type
    """

    ...


class DeveloperDataIDMessage:
    """
    A DeveloperDataIDMessage is used to uniquely identify developer data field sources
    """
    application_id: UUID
    developer_data_index: int

    def __init__(self, application_id: UUID, developer_data_index: int):
        self.application_id = application_id
        self.developer_data_index = developer_data_index

    @classmethod
    def from_data(cls, data: BinaryIO) -> DeveloperDataIDMessage:
        part_a, part_b = struct.unpack('QQ', data.read(16))
        application_id = (part_a << 64) | part_b
        developer_data_index = struct.unpack('B', data.read(1))
        return cls(application_id, developer_data_index)

    decode = from_data

    def encode(self) -> bytes:
        max_int64 = 0xFFFFFFFFFFFFFFFF
        struct.pack('QQ', (self.application_id.int >> 64) & max_int64, self.application_id.int & max_int64)
