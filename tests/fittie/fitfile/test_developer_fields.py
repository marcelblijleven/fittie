from io import BytesIO

import pytest

from fittie import DecodeOptions, Encoder, decode, encode
from tests.fittie.fitfile.test_protocol import definition, fit_bytes


def developer_definition(local=0, number=20, fields=(), developers=((0, 2, 0),)):
    result = bytearray(definition(local, number, fields))
    result[0] |= 0x20
    result += bytes([len(developers)])
    for field in developers:
        result += bytes(field)
    return bytes(result)


def descriptor(writer, index, name, base=0x84, **metadata):
    writer.write("developer_data_id", {"developer_data_index": index})
    writer.write(
        "field_description",
        {
            "developer_data_index": index,
            "field_definition_number": 0,
            "fit_base_type_id": base,
            "field_name": name,
            **metadata,
        },
    )


@pytest.mark.parametrize("endian", ["<", ">"])
def test_typed_developer_values_do_not_use_native_scale(endian):
    writer = Encoder()
    descriptor(
        writer,
        0,
        "custom",
        0x88,
        native_mesg_num=20,
        native_field_num=54,
        scale=100,
        offset=2,
    )
    writer.write(
        "record",
        {"heart_rate": 120},
        developer_fields={(0, 0): [1.25, None, 2.5]},
        endianness=endian,
    )
    file = decode(BytesIO(writer.to_bytes()))[0]
    assert file.messages[-1].fields["custom"] == [1.25, None, 2.5]
    assert file.messages[-1].developer_fields == {(0, 0): [1.25, None, 2.5]}
    assert file.developer_data[0]["fields"][0].metadata["scale"] == 100
    assert (
        decode(BytesIO(encode(file)))[0].messages[-1].developer_fields
        == file.messages[-1].developer_fields
    )


def test_collisions_preserve_native_and_both_developers():
    writer = Encoder()
    descriptor(writer, 0, "heart_rate", 2)
    descriptor(writer, 1, "heart_rate", 2)
    writer.write(
        "record", {"heart_rate": 120}, developer_fields={(0, 0): 110, (1, 0): 130}
    )
    message = decode(BytesIO(writer.to_bytes()))[0].messages[-1]
    assert message.fields == {
        "heart_rate": 120,
        "developer_0_0_heart_rate": 110,
        "developer_1_0_heart_rate": 130,
    }
    assert message.developer_fields == {(0, 0): 110, (1, 0): 130}


def test_missing_description_retains_opaque_bytes_and_alignment():
    payload = (
        developer_definition(fields=((3, 1, 2),)) + b"\0\x78\x12\x34\0\x79\x56\x78"
    )
    file = decode(BytesIO(fit_bytes(payload)))[0]
    assert [m.fields["heart_rate"] for m in file.messages] == [120, 121]
    assert file.messages[0].developer_fields == {(0, 0): b"\x12\x34"}
    assert decode(BytesIO(encode(file)))[0].messages[0].developer_fields == {
        (0, 0): b"\x12\x34"
    }


def test_unknown_developer_type_and_missing_name_are_retained():
    writer = Encoder()
    writer.write(
        "field_description",
        {
            "developer_data_index": 0,
            "field_definition_number": 0,
            "fit_base_type_id": 31,
        },
    )
    writer.write("record", {"heart_rate": 120}, developer_fields={(0, 0): b"\x01\xff"})
    message = decode(BytesIO(writer.to_bytes()))[0].messages[-1]
    assert message.fields["developer_0_0"] == b"\x01\xff"


def test_native_override_is_explicit_and_uses_physical_units():
    writer = Encoder()
    descriptor(writer, 0, "custom_hr", 2, native_mesg_num=20, native_field_num=3)
    writer.write("record", {"heart_rate": 120}, developer_fields={(0, 0): 130})
    assert (
        decode(BytesIO(writer.to_bytes()))[0].messages[-1].fields["heart_rate"] == 120
    )
    result = decode(
        BytesIO(writer.to_bytes()), options=DecodeOptions(apply_native_overrides=True)
    )[0]
    assert result.messages[-1].fields["heart_rate"] == 130


def test_string_arrays_and_base_type_number_without_endian_flag():
    writer = Encoder()
    descriptor(writer, 0, "labels", 7)
    writer.write("record", {}, developer_fields={(0, 0): ["é", "two"]})
    assert decode(BytesIO(writer.to_bytes()))[0].messages[-1].fields["labels"] == [
        "é",
        "two",
    ]
    # Some contributors supply the base-type number (4), not its wire id (0x84).
    writer = Encoder()
    descriptor(writer, 0, "number", 4)
    writer.write("record", {}, developer_fields={(0, 0): 300})
    assert decode(BytesIO(writer.to_bytes()))[0].messages[-1].fields["number"] == 300


def test_developer_mapping_edits_are_isolated_and_encode():
    writer = Encoder()
    descriptor(writer, 0, "custom", 2)
    writer.write("record", {}, developer_fields={(0, 0): 120})
    writer.write("record", {}, developer_fields={(0, 0): 121})
    file = decode(BytesIO(writer.to_bytes()))[0]
    first, second = file.messages[-2:]
    first.developer_fields[(0, 0)] = 130
    assert second.developer_fields[(0, 0)] == 121
    assert decode(BytesIO(encode(file)))[0].messages[-2].fields["custom"] == 130
    first.developer_fields[(1, 0)] = 99
    del first.developer_fields[(1, 0)]
    assert dict(first.developer_fields) == {(0, 0): 130}
    with pytest.raises(KeyError):
        del first.developer_fields[(1, 0)]
    with pytest.raises(KeyError):
        first.developer_fields[(1, 0)]


@pytest.mark.parametrize(
    "developers", [((0, 0, 0),), ((255, 2, 0),), ((0, 2, 255),), ((0, 2, 0), (0, 2, 0))]
)
def test_invalid_developer_definitions_are_rejected(developers):
    from fittie.fitfile.utils.exceptions import DecodeException

    with pytest.raises(DecodeException, match="developer field definition"):
        decode(BytesIO(fit_bytes(developer_definition(developers=developers))))


def test_reused_developer_index_resets_old_application_descriptions():
    writer = Encoder()
    writer.write(
        "file_id", {"type": "settings", "manufacturer": 1, "time_created": 100}
    )
    writer.write(
        "developer_data_id", {"developer_data_index": 0, "application_id": [1] * 16}
    )
    writer.write(
        "field_description",
        {
            "developer_data_index": 0,
            "field_definition_number": 0,
            "fit_base_type_id": 2,
            "field_name": "old",
        },
    )
    writer.write("record", {}, developer_fields={(0, 0): 120})
    writer.write(
        "developer_data_id", {"developer_data_index": 0, "application_id": [2] * 16}
    )
    writer.write("record", {}, developer_fields={(0, 0): b"x"})
    file = decode(BytesIO(writer.to_bytes()))[0]
    assert file.messages[-1].fields == {"developer_0_0": b"x"}
    assert (
        decode(BytesIO(encode(file)))[0].messages[-1].fields == file.messages[-1].fields
    )

    assert any(issue.code == "developer_description" for issue in file.validate())
