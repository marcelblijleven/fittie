"""Synthetic protocol fixtures keep boundary cases independent of SDK downloads."""

import struct
from io import BytesIO

import pytest

from fittie import decode
from fittie.fitfile.crc import calculate_crc
from fittie.fitfile.decode import decode_file_type
from fittie.fitfile.field_definitions import FieldDefinition, read_field
from fittie.fitfile.header import decode_header
from fittie.fitfile.utils.exceptions import DecodeException
from fittie.profile.base_types import BASE_TYPES


def fit_bytes(payload=b"", *, header_size=14, header_crc=True):
    header = struct.pack("<BBHI4s", header_size, 0x20, 21217, len(payload), b".FIT")
    if header_size >= 14:
        header += bytes(header_size - 14)
        header += struct.pack("<H", calculate_crc(header) if header_crc else 0)
    content = header + payload
    return content + struct.pack("<H", calculate_crc(content))


def definition(local, global_number, fields, *, big_endian=False):
    return (
        bytes([0x40 | local, 0, int(big_endian)])
        + struct.pack(">H" if big_endian else "<H", global_number)
        + bytes([len(fields)])
        + b"".join(bytes(field) for field in fields)
    )


def file_id():
    return definition(0, 0, [(0, 1, 0)]) + bytes([0, 4])


@pytest.mark.parametrize("calculate", [True, False])
@pytest.mark.parametrize("header_size", [12, 14, 16])
def test_chained_members_at_nonzero_stream_position(calculate, header_size):
    member = fit_bytes(file_id(), header_size=header_size)
    source = BytesIO(b"prefix" + member * 3)
    source.read(6)
    fitfiles = decode(source, calculate_crc=calculate)
    assert [file.file_type for file in fitfiles] == ["activity"] * 3
    assert source.tell() == 6 + len(member) * 3
    assert not source.closed


@pytest.mark.parametrize("calculate", [True, False])
def test_every_truncation_is_rejected(calculate):
    member = fit_bytes(file_id())
    for length in range(1, len(member)):
        with pytest.raises(DecodeException):
            decode(BytesIO(member[:length]), calculate_crc=calculate)
    with pytest.raises(DecodeException):
        decode(BytesIO(member + member[:-1]), calculate_crc=calculate)


@pytest.mark.parametrize("calculate", [True, False])
def test_record_cannot_consume_crc_as_data(calculate):
    payload = definition(0, 20, [(253, 4, 0x86)]) + b"\x00\x01\x02"
    with pytest.raises(DecodeException, match="beyond the FIT data section"):
        decode(BytesIO(fit_bytes(payload)), calculate_crc=calculate)


def test_zero_header_crc_is_permitted():
    assert (
        decode(BytesIO(fit_bytes(file_id(), header_crc=False)))[0].file_type
        == "activity"
    )


@pytest.mark.parametrize("byte,value", [(0, 11), (0, 13), (1, 0x30), (8, ord("X"))])
def test_invalid_headers_even_without_crc(byte, value):
    content = bytearray(fit_bytes(file_id()))
    content[byte] = value
    with pytest.raises(DecodeException):
        decode(BytesIO(content), calculate_crc=False)


def test_header_encoding_is_repeatable():
    content = fit_bytes(file_id(), header_size=16)
    header = decode_header(BytesIO(content))
    assert header.encode() == header.encode() == content[:16]


def test_file_crc_is_checked_and_can_be_disabled():
    content = fit_bytes(file_id())
    damaged = content[:-1] + bytes([content[-1] ^ 1])
    with pytest.raises(DecodeException, match="crc"):
        decode(BytesIO(damaged))
    assert decode(BytesIO(damaged), calculate_crc=False)[0].file_type == "activity"


def test_header_crc_is_checked():
    content = bytearray(fit_bytes(file_id()))
    content[12] ^= 1
    with pytest.raises(DecodeException, match="crc.*header"):
        decode(BytesIO(content))


@pytest.mark.parametrize("timestamp_in_definition", [True, False])
@pytest.mark.parametrize("big_endian", [True, False])
def test_compressed_timestamps_roll_over_across_local_messages(
    timestamp_in_definition, big_endian
):
    timestamp = [(253, 4, 0x86)]
    heart_rate = [(3, 1, 2)]
    payload = definition(0, 20, timestamp, big_endian=big_endian)
    payload += b"\x00" + struct.pack(">I" if big_endian else "<I", 59)
    for local, offset in [(1, 27), (2, 29), (3, 2), (1, 5)]:
        fields = timestamp + heart_rate if timestamp_in_definition else heart_rate
        payload += definition(local, 20, fields, big_endian=big_endian)
        payload += bytes([0x80 | (local << 5) | offset, 120])
    # A full timestamp resets the reference, including when time moves backwards.
    payload += b"\x00" + struct.pack(">I" if big_endian else "<I", 32)
    payload += bytes([0xA1, 121])
    records = decode(BytesIO(fit_bytes(payload)))[0].get_messages_by_type("record")
    assert [record.fields["timestamp"] for record in records] == [
        59,
        59,
        61,
        66,
        69,
        32,
        33,
    ]
    assert records[-1].fields["heart_rate"] == 121


def test_compressed_timestamp_requires_reference_in_each_chained_file():
    full = definition(0, 20, [(253, 4, 0x86)]) + b"\x00" + struct.pack("<I", 59)
    compressed = definition(1, 20, [(3, 1, 2)]) + bytes([0xA0, 120])
    with pytest.raises(DecodeException, match="preceding full timestamp"):
        decode(BytesIO(fit_bytes(full) + fit_bytes(compressed)))


def test_decode_file_type_reads_record_header_once():
    assert decode_file_type(BytesIO(fit_bytes(file_id()))) == "activity"


@pytest.mark.parametrize("base_type", [0x88, 0x89])
@pytest.mark.parametrize("endianness", ["<", ">"])
def test_float_invalid_value_uses_bit_pattern(base_type, endianness):
    base = BASE_TYPES[base_type]
    assert base.get_value(endianness, BytesIO(b"\xff" * base.size)) is None
    assert (
        base.get_value(endianness, BytesIO(struct.pack(endianness + base.fmt, 1.25)))
        == 1.25
    )


@pytest.mark.parametrize(
    "raw,expected",
    [(b"\x00\x00", [0, 0]), (b"\xff\xff", None), (b"\x00\xff", [0, None])],
)
def test_numeric_arrays_preserve_zero_values(raw, expected):
    assert (
        read_field(FieldDefinition(1, len(raw), BASE_TYPES[2]), "<", BytesIO(raw))
        == expected
    )


@pytest.mark.parametrize(
    "raw,expected",
    [(b"a", "a"), (b"\x00", None), (b"a\x00b\x00", ["a", "b"]), (b"\xc3\xa9\x00", "é")],
)
def test_strings_and_string_arrays_are_utf8_and_nul_terminated(raw, expected):
    assert (
        read_field(FieldDefinition(1, len(raw), BASE_TYPES[7]), "<", BytesIO(raw))
        == expected
    )


@pytest.mark.parametrize("size", [0, 3])
def test_invalid_field_sizes_are_rejected(size):
    with pytest.raises(DecodeException, match="field size"):
        read_field(
            FieldDefinition(1, size, BASE_TYPES[0x84]), "<", BytesIO(bytes(size))
        )


def test_unknown_messages_and_fields_remain_decodable():
    payload = definition(0, 0xFF01, [(42, 2, 0x84)], big_endian=True) + b"\x00\x01\x02"
    message = decode(BytesIO(fit_bytes(payload)))[0].data_messages["unknown_65281"][0]
    assert message.fields == {"unknown_65281_unknown_field_42": 258}
