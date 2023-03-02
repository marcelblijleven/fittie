from __future__ import annotations  # Added for type hints

import functools
import itertools

from abc import ABC, abstractmethod
from typing import Any, Optional, Iterable

from fittie.fitfile.profile.messages import MESSAGES
from fittie.fitfile.data_message import DataMessage
from fittie.fitfile.definition_message import DefinitionMessage
from fittie.fitfile.header import Header
from fittie.fitfile.profile.fit_types import FIT_TYPES
from fittie.fitfile.profile.mesg_nums import MESG_NUMS
from fittie.fitfile.util import datetime_from_timestamp


class _IterableMixin(ABC):
    @property
    @abstractmethod
    def _iter_collection(self):
        """
        Defines which collection of data the __next__ method should use.

        Make sure to decorate this with @cached_property if it is an expensive
        calculation.

        Also make sure to add __dict__ to  __slots__ if slots are used and the
        property is cached, because  __dict__ has to be mutable.
        """
        ...

    def __next__(self) -> dict:
        if self._iter_index >= len(self._iter_collection):
            # Remove _iter_collection value from cache, if it exists.
            # If _iter_collection is cached, then it should exist and be cleared
            # as soon as the collection has been fully iterated.
            if "_iter_collection" in self.__dict__:
                del self.__dict__["_iter_collection"]

            # Remove _iter_file from dict, because it is only used in iterations
            if "_iter_filter" in self.__dict__:
                del self.__dict__["_iter_filter"]

            raise StopIteration

        value = self._iter_collection[self._iter_index]
        self._iter_index += 1

        if hasattr(self, "_iter_filter") and (fields := self._iter_filter["fields"]):
            return {field: value.fields.get(field) for field in fields}

        return value.fields

    def __iter__(self):
        self._iter_index = 0
        return self


class FitFile(_IterableMixin):

    header: Header
    data_messages: dict[str, list[DataMessage]]
    local_message_definitions: dict[int, DefinitionMessage] = {}
    developer_data: dict[int, dict[str, Any]] = {}  # TODO: add typing

    def __init__(
        self,
        header: Header,
        data_messages: dict[str, list[DataMessage]],
        local_message_definitions: dict[int, DefinitionMessage],
        developer_data: dict[int, dict[str, Any]],
    ):
        self.header = header
        self.data_messages = data_messages
        self.local_message_definitions = local_message_definitions
        self.developer_data = developer_data

    @functools.cached_property
    def _iter_collection(self) -> Iterable[DataMessage]:
        if hasattr(self, "_iter_filter"):
            # Entered through __call__, filter messages
            message_type = self._iter_filter["message_type"]
            return self.data_messages.get(message_type, [])

        return list(itertools.chain(*self.data_messages.values()))

    def __call__(self, *, message_type: str, fields: Optional[list[str]] = None):
        """
        Makes the instance callable and adds filter options for a specific message
        type and keywords of field values to return while iterating
        """
        self._iter_filter = {
            "fields": fields or [],
            "message_type": message_type,
        }

        return self

    @property
    def file_id(self) -> Optional[dict[str, Any]]:
        """
        Get file id information.

        Raw values from the FIT file will be filled with information from the Garmin
        FIT SDK Fit Types
        """
        if not (file_id_messages := self.data_messages.get("file_id")):
            raise ValueError(
                "no file_id message detected, FIT file is possible incorrect"
            )

        file_id = {}

        # Should be just one file_id, but to be sure use latest from list
        for key, value in file_id_messages[-1].fields.items():
            if key == "time_created":
                file_id[key] = datetime_from_timestamp(value)
            elif key == "type":
                file_id[key] = FIT_TYPES["file"]["values"][value]["value_name"]
            elif key == "manufacturer":
                file_id[key] = FIT_TYPES["manufacturer"]["values"][value]["value_name"]
            else:
                file_id[key] = value

        return file_id

    @property
    def file_type(self) -> str:
        """
        Returns the file type of the FIT File. The file type is retrieved from the
        file_id message, which is always present in a FIT file.
        """
        return self.file_id["type"]

    @property
    def available_message_types(self) -> list[str]:
        """Returns a list of all message types that this FIT file contains"""
        return list(self.data_messages.keys())

    @functools.cached_property
    def available_fields(self) -> dict[str, str]:
        """Returns a list of all field names as key, with units as value"""
        fields = {}

        for definition_message in self.local_message_definitions.values():
            _fields = MESSAGES[definition_message.global_message_type]["fields"]

            for field_definition in definition_message.field_definitions:
                field = _fields[field_definition.number]
                fields[field["field_name"]] = field["units"]

        return fields

    def get_messages_by_type(self, message_type: str) -> list[DataMessage]:
        """
        Returns all messages of the provided type, if the FIT file contains these
        messages. If not, it will return an empty list.

        If the provided message type is unknown, a ValueError will be raised.
        """
        if message_type not in MESG_NUMS.values():
            raise ValueError(f"unknown message type '{message_type}' received")

        return self.data_messages.get(message_type, [])
