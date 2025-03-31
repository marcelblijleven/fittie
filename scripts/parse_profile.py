import dataclasses
import fileinput
import logging
import pprint
import re

from black import format_str, FileMode
from csv import DictReader
from datetime import datetime
from typing import Any, Optional, Union, cast

from fittie.fitfile.profile import MessageProfile, FieldProfile, SubField
from fittie.fitfile.profile.field_type import FieldType, FieldTypeValue
from fittie.fitfile.profile.mesg_nums import MESG_NUMS
from fittie.fitfile.profile.fit_types import FIT_TYPES

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

WIDTH = 88

DELIMITER = ";"
TYPES_TYPE_NAME_COLUMN = "Type Name"
TYPES_BASE_TYPE_COLUMN = "Base Type"
TYPES_VALUE_NAME_COLUMN = "Value Name"
TYPES_VALUE_COLUMN = "Value"
TYPES_COMMENT_COLUMN = "Comment"

MESSAGES_MESSAGE_NAME_COLUMN = "Message Name"
MESSAGES_DEFINITION_NUMBER_COLUMN = "Field Def #"
MESSAGES_FIELD_NAME_COLUMN = "Field Name"
MESSAGES_FIELD_TYPE_COLUMN = "Field Type"
MESSAGES_ARRAY_COLUMN = "Array"
MESSAGES_COMPONENTS_COLUMN = "Components"
MESSAGES_SCALE_COLUMN = "Scale"
MESSAGES_OFFSET_COLUMN = "Offset"
MESSAGES_UNITS_COLUMN = "Units"
MESSAGES_BITS_COLUMN = "Bits"
MESSAGES_ACCUMULATE_COLUMN = "Accumulate"
MESSAGES_REF_FIELD_NAME_COLUMN = "Ref Field Name"
MESSAGES_REF_FIELD_VALUE_COLUMN = "Ref Field Value"
MESSAGES_COMMENT_COLUMN = "Comment"
MESSAGES_PRODUCTS_COLUMN = "Products:"
MESSAGES_EXAMPLE_COLUMN = "EXAMPLE"


def get_file_header() -> str:
    text = f"This file is auto generated at {datetime.now()}, do not edit this file"
    prepend = f'#{" " * int((WIDTH - len(text)) / 2 - 1)}'
    padding = "#" * WIDTH

    return "\n".join([padding, f"{prepend}{text}{prepend[::-1]}", padding])


def get_value(row: dict[str, Any], key: str) -> Optional[Union[str, int, list[int]]]:
    value = row.get(key)

    # Check for empty value
    if value is None or value == "":
        return None

    try:
        parsed = int(value)
    except ValueError:
        return value

    return parsed


def can_ignore_row(row: dict[str, Any]) -> bool:
    if (
            field_type := get_value(row, MESSAGES_FIELD_TYPE_COLUMN)
    ) and field_type == field_type.upper():
        return True
    return False


def read_csv(filename: str) -> DictReader:
    with open(filename, "r") as f:
        lines = f.readlines()
        fieldnames = lines[0].strip().split(DELIMITER)
        return DictReader(lines[1:], fieldnames, delimiter=DELIMITER)


def get_array_value(value: Optional[str]) -> Union[bool, int, str]:
    """
    Tries to retrieve an array value from the provided value

    - When the value is None or empty, False is returned
    - When the value between [] is a number, that number is returned
    - When the value between [] is "N", "N" is returned
    """
    if value is None or value == "":
        return False

    if "N" in value:
        return "N"

    if match := re.search(r"(\d+)", value):
        return int(match.group())

    return False


def get_components(value: Optional[str]) -> Optional[Union[str, list[str]]]:
    """
    Tries to retrieve components from the provided value
    """
    if value is None or value == "":
        return None

    if "," not in value:
        return value

    return value.split(",")


def get_scale(
        value: Optional[str], units: str
) -> Optional[Union[int, float, list[int]]]:
    """
    Tries to retrieve scale from the provided value

    - When the provided units are degrees or radians, the value will be parsed to float
    - When the provided value can be parsed to an int, the int will be returned
    - When the provided value is a list of ints, that list will be returned
    """
    if value is None or value == "":
        return None

    if isinstance(value, int):
        return value

    if units == "degrees" or units == "radians":
        return float(value.replace(",", "."))

    return [int(v) for v in value.split(",")]


def get_accumulate(value: Optional[str]) -> Optional[Union[int, list[int]]]:
    return get_scale(value, "")


def read_messages() -> dict[str, Any]:
    reader = read_csv("./data/Messages.csv")
    mesg_num_lookup = {v: k for k, v in MESG_NUMS.items()}
    messages = {}
    last_message_num = None
    group = None

    logger.debug("starting with parsing messages")

    field_map = {}
    last_field = None

    for row in reader:
        if can_ignore_row(row):
            group = get_value(row, MESSAGES_FIELD_TYPE_COLUMN)
            continue

        if (message_name := get_value(row, MESSAGES_MESSAGE_NAME_COLUMN)) is not None:
            last_message_name = message_name
            last_message_num = mesg_num_lookup[last_message_name]
            messages[last_message_num] = MessageProfile(last_message_name, {}, group)
        else:
            definition_number = get_value(row, MESSAGES_DEFINITION_NUMBER_COLUMN)

            array_value = get_array_value(get_value(row, MESSAGES_ARRAY_COLUMN))
            field = FieldProfile(
                field_name=get_value(row, MESSAGES_FIELD_NAME_COLUMN),
                field_type=get_value(row, MESSAGES_FIELD_TYPE_COLUMN),
                array=array_value,
                components=get_components(
                    get_value(row, MESSAGES_COMPONENTS_COLUMN)
                ),
                scale=get_scale(
                    get_value(row, MESSAGES_SCALE_COLUMN),
                    get_value(row, MESSAGES_UNITS_COLUMN),
                ),
                offset=get_value(row, MESSAGES_OFFSET_COLUMN),
                units=get_value(row, MESSAGES_UNITS_COLUMN),
                bits=get_value(row, MESSAGES_BITS_COLUMN),
                accumulate=get_accumulate(
                    get_value(row, MESSAGES_ACCUMULATE_COLUMN)
                ),
                # "ref_field_name": get_components(
                #     get_value(row, MESSAGES_REF_FIELD_NAME_COLUMN)
                # ),
                # "ref_field_value": get_components(
                #     get_value(row, MESSAGES_REF_FIELD_VALUE_COLUMN)
                # ),
                subfields=[],
                comment=get_value(row, MESSAGES_COMMENT_COLUMN),
            )

            if definition_number is not None:
                # Regular field
                messages[last_message_num].fields[definition_number] = field
                field_map[field.field_name] = definition_number, field
                last_field = field
            else:
                # Subfield
                field_as_dict = dataclasses.asdict(field)
                field_as_dict["ref_field_name"] = get_components(
                    get_value(row, MESSAGES_REF_FIELD_NAME_COLUMN)
                )
                field_as_dict["ref_field_value"] = get_components(
                    get_value(row, MESSAGES_REF_FIELD_VALUE_COLUMN)
                )
                field_as_dict["refs"] = []
                del field_as_dict["accumulate"]
                del field_as_dict["subfields"]
                #
                # if isinstance(ref_field_name, list):
                #     for name, value in zip(ref_field_name, ref_field_value):
                #         ref_field_number, ref_field = field_map[name]
                #
                #         values = FIT_TYPES[ref_field["field_type"]]["values"]
                #
                #         for value_number, data in values.items():
                #             if data["value_name"] == value:
                #                 field["ref"].append({
                #                     "field_number": ref_field_number,
                #                     "value_number": value_number,
                #                     "value_name": value,
                #                     "field_name": name,
                #                 }
                #                 )
                #
                # else:
                #     ref_field_number, ref_field = field_map[ref_field_name]
                #
                #     values = FIT_TYPES[ref_field["field_type"]]["values"]
                #
                #     for value_number, data in values.items():
                #         if data["value_name"] == ref_field_value:
                #             field["ref"].append({
                #                 "field_number": ref_field_number,
                #                 "value_number": value_number,
                #                 "value_name": ref_field_value,
                #                 "field_name": ref_field_name,
                #             }
                #             )

                last_field.subfields.append(SubField(**field_as_dict))

    add_subfield_refs(messages, field_map)
    logger.debug(f"parsing messages finished, {len(messages.keys())} messages parsed")

    return messages


def add_subfield_refs(messages: dict, field_map: dict):
    for message_number, message in messages.items():
        for field_number, field in message.fields.items():
            for subfield in field.subfields:
                ref_field_name = subfield.ref_field_name
                ref_field_value = subfield.ref_field_value

                if isinstance(ref_field_name, str):
                    subfield.refs.append(
                        find_subfield_ref(ref_field_name, ref_field_value, field_map)
                    )
                else:
                    for name, value in zip(ref_field_name, ref_field_value):
                        subfield.refs.append(
                            find_subfield_ref(name, value, field_map)
                        )


def find_subfield_ref(name: str, value: str, field_map: dict) -> dict:
    number, field = field_map[name]
    fit_type_values = FIT_TYPES[field.field_type].values

    for value_number, data in fit_type_values.items():
        if data.value_name == value:
            return {
                "field_number": number,
                "value_number": value_number,
                "value_name": value,
                "field_name": name,
            }


def read_types() -> dict[str, Any]:
    reader = read_csv("./data/Types.csv")

    types: dict[str, FieldType] = {}
    last_type_name = None

    logger.debug("starting with parsing types")

    for row in reader:
        if (type_name := get_value(row, TYPES_TYPE_NAME_COLUMN)) is not None:
            types[type_name] = FieldType(base_type=get_value(row, TYPES_BASE_TYPE_COLUMN), values={})
            last_type_name = type_name
        else:
            value_name = row[TYPES_VALUE_NAME_COLUMN]
            value = row[TYPES_VALUE_COLUMN]
            comment = row.get(TYPES_COMMENT_COLUMN, "")

            if "x" in value:
                parsed_value = int(value, 16)
                comment += f" (original value: {value})"
                comment = comment.lstrip()
            else:
                parsed_value = int(value)

            types[last_type_name].values[parsed_value] = FieldTypeValue(value_name=value_name, comment=comment)

    logger.debug(f"parsing types finished, {len(types.keys())} types parsed")

    return types


def write_types_to_file(types: dict[str, Any]) -> None:
    import_text = "from fittie.fitfile.profile.field_type import FieldType, FieldTypeValue"
    __write_to_file(types, "../fittie/fitfile/profile/fit_types.py", "FIT_TYPES", import_text)


def write_messages_to_file(messages: dict[str, Any]) -> None:
    import_text = "from fittie.fitfile.profile.message_profile import MessageProfile, FieldProfile, SubField"
    __write_to_file(messages, "../fittie/fitfile/profile/messages.py", "MESSAGES", import_text)


def __write_to_file(
        dict_value: dict[str, Any], filename: str, variable_name: str, import_text: str
) -> None:
    with open(filename, "w") as f:
        file_header = get_file_header()
        pretty = pprint.pformat(dict_value, width=WIDTH, compact=True, sort_dicts=False)
        f.write(
            format_str(f"{file_header}\n{import_text}\n{variable_name} = {pretty}", mode=FileMode())
        )


def write_profile_version():
    import ast

    with open("data/version.txt") as file:
        version = file.read().rstrip("\n")

    # Hacky solution
    for line in fileinput.input("../fittie/__init__.py", inplace=True):
        if "__PROFILE_VERSION__" in line:
            print(f"__PROFILE_VERSION__ = \"{version}\"", end="\n")
        else:
            print(line, end="")


if __name__ == "__main__":
    write_types_to_file(read_types())
    write_messages_to_file(read_messages())
    write_profile_version()
