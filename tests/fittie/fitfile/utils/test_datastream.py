import io
import tempfile

import pytest

from fittie.fitfile.crc import calculate_crc
from fittie.fitfile.utils.datastream import DataStream


def test_datastream_file():
    with tempfile.NamedTemporaryFile("rb") as file:
        DataStream(file)  # Should not raise
        assert DataStream.is_file(file)


def test_datastream_file__invalid_mode():
    with tempfile.NamedTemporaryFile("r") as file:
        with pytest.raises(IOError) as exc_info:
            DataStream(file)

    assert "expected file to be opened with mode 'rb', got 'r'" in str(exc_info.value)


def test_datastream_path():
    with tempfile.NamedTemporaryFile("rb") as file:
        DataStream(file.name)  # Should not raise
        assert DataStream.is_path(file.name)


def test_datastream_path__file_does_not_exist():
    with pytest.raises(FileNotFoundError) as exc_info:
        DataStream("/does/not/exist.fit")

    assert "file /does/not/exist.fit does not exist" in str(exc_info.value)


def test_datastream_streamable():
    data = io.BytesIO(b"123")
    DataStream(data)  # Should not raise
    assert DataStream.is_streamable(data)


def test_datastream_invalid_value():
    with pytest.raises(ValueError) as exc_info:
        DataStream(bytes([1, 2, 3]))

    assert "unsupported value received as stream input: <class 'bytes'>" in str(
        exc_info.value
    )


def test_datastream_crc():
    datastream = DataStream(io.BytesIO(b"123456"))
    assert datastream.calculated_crc == 0
    assert datastream.read(2) == b"12"
    assert datastream.calculated_crc == calculate_crc(b"12")
    assert datastream.read(4) == b"3456"
    assert datastream.calculated_crc == calculate_crc(b"123456")


def test_datastream_crc__crc_disabled():
    datastream = DataStream(io.BytesIO(b"123"))
    datastream.should_calculate_crc = False
    assert datastream.read(3) == b"123"
    assert datastream.calculated_crc == 0


def test_position_tracks_reads_and_partial_reads():
    source = io.BytesIO(b"prefix123")
    source.read(6)
    with DataStream(source) as stream:
        assert stream.tell() == 6
        assert stream.read(2) == b"12"
        assert stream.tell() == 8
        with pytest.raises(EOFError):
            stream.read(2)
        assert stream.tell() == 9
    assert not source.closed


def test_reopening_owned_stream_resets_position(tmp_path):
    path = tmp_path / "stream.bin"
    path.write_bytes(b"123")
    stream = DataStream(path)
    for _ in range(2):
        with stream:
            assert stream.tell() == 0
            assert stream.read(3) == b"123"
            assert stream.tell() == 3
