import io
from unittest.mock import patch

import pytest
import tempfile

from fittie.utils.datastream import DataStream
from fittie.fitfile.crc import apply_crc


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
    datastream = DataStream(io.BytesIO(b"123"))
    assert datastream.calculated_crc == 0

    with patch(
        "fittie.utils.datastream.apply_crc", side_effect=apply_crc
    ) as patched_apply_crc:
        datastream.read()

    assert datastream.calculated_crc != 0
    patched_apply_crc.assert_called_once()


def test_datastream_crc__crc_disabled():
    datastream = DataStream(io.BytesIO(b"123"))
    datastream.should_calculate_crc = False
    assert datastream.calculated_crc == 0

    with patch(
        "fittie.utils.datastream.apply_crc", side_effect=apply_crc
    ) as patched_apply_crc:
        datastream.read()

    assert datastream.calculated_crc == 0
    patched_apply_crc.assert_not_called()
