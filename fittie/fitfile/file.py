import logging
import os

from collections import defaultdict
from typing import BinaryIO, Any, DefaultDict, Optional

from fittie.fitfile.data_message import DataMessage
from fittie.fitfile.definition_message import DefinitionMessage
from fittie.fitfile.header import Header, decode_header
from fittie.fitfile.profile.base_types import BASE_TYPES
from fittie.fitfile.profile.fit_types import FIT_TYPES
from fittie.fitfile.profile.mesg_nums import MESG_NUMS
from fittie.fitfile.records import read_record_header, read_record
from fittie.fitfile.util import datetime_from_timestamp

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL)
logger = logging.getLogger("fittie")


class FitFile:
    header: Header
    messages: dict[str, list[DataMessage]]

    def __init__(self, header: Header, messages: dict[str, list[DataMessage]]):
        self.header = header
        self.messages = messages

    @property
    def average_heart_rate(self) -> Optional[int]:
        """Get average heart rate from data messages, if any"""
        heart_rates: list[int] = []

        if not (records := self.messages.get("record")):
            return None

        for message in records:
            if (heart_rate := message.fields.get("heart_rate")) is not None:
                heart_rates.append(heart_rate)
        if not heart_rates:
            return None

        return int(sum(heart_rates) / len(heart_rates))

    @property
    def file_id(self) -> Optional[dict[str, Any]]:
        """
        Get file id information.

        Raw values from the FIT file will be filled with information from the Garmin
        FIT SDK Fit Types
        """
        if not (file_ids := self.messages.get("file_id")):
            return None

        file_id = {}

        # Should be just one file_id, but to be sure use latest from list
        for key, value in file_ids[-1].fields.items():
            if key == "time_created":
                file_id[key] = datetime_from_timestamp(value)
            elif key == "type":
                file_id[key] = FIT_TYPES["file"]["values"][value]["value_name"]
            elif key == "manufacturer":
                file_id[key] = FIT_TYPES["manufacturer"]["values"][value]["value_name"]
            else:
                file_id[key] = value

        return file_id


def decode(data: BinaryIO) -> FitFile:
    """
    Decode a fit file
    """
    header = decode_header(data)

    logger.debug(header)

    local_message_definitions: dict[int, DefinitionMessage] = {}
    developer_data: dict[int, dict[str, Any]] = {}  # TODO: add typing
    messages: DefaultDict[str, list[DataMessage]] = defaultdict(list)

    while data.tell() < header.data_size:
        # Read record header
        record_header = read_record_header(data)
        logger.debug(record_header)

        # Read message
        message = read_record(
            record_header,
            local_message_definitions.get(record_header.local_message_type),
            developer_data,
            data,
        )
        logger.debug(message)

        # Assign message to correct collection
        if record_header.is_compressed_timestamp_message:
            # TODO:
            ...
        elif record_header.is_developer_data or record_header.is_definition_message:
            # TODO: check if this can be merged with is_definition_message
            local_message_definitions[record_header.local_message_type] = message
        else:
            # TODO: move this to separate function
            if (
                global_message_type := local_message_definitions.get(
                    record_header.local_message_type
                ).global_message_type
            ) == 207:
                # Add developer data index
                index = message.fields["developer_data_index"]
                developer_data[index] = message.fields
                developer_data[index].update({"fields": {}})
            elif global_message_type == 206:
                # Add field descriptions
                index = message.fields["developer_data_index"]
                field = message.fields
                # TODO: make class/type for FieldDescription
                developer_data[index]["fields"][field["field_definition_number"]] = {
                    "data_index": field["developer_data_index"],
                    "number": field["field_definition_number"],
                    "name": field["field_name"],
                    "base_type": BASE_TYPES[field["fit_base_type_id"]],
                    "native_message_number": field.get("native_mesg_num"),
                    "native_field_number": field.get("native_field_num"),
                    "units": field.get("units"),
                }

            messages[MESG_NUMS[global_message_type]].append(message)

    fitfile = FitFile(header=header, messages=messages)

    return fitfile
