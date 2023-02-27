from unittest import mock
from functools import cached_property

from fittie.fitfile.fitfile import _IterableMixin  # noqa


class Message:
    fields = {"a": 1, "b": 2, "c": 3}


def compute() -> list:
    return [Message(), Message(), Message()]


class FooCached(_IterableMixin):
    @cached_property
    def _iter_collection(self):
        return compute()


def test_iterable():
    foo = FooCached()
    lst = [Message(), Message(), Message()]

    with mock.patch(
        "tests.fittie.fitfile.test_iterable.compute", return_value=lst
    ) as mock_compute:
        for value in foo:
            # Assert fields property is returned
            assert value == {"a": 1, "b": 2, "c": 3}

        # Assert property is cached
        mock_compute.assert_called_once()


def test_iterable_fitfile(small_fitfile):
    messages = []

    for message in small_fitfile:
        assert isinstance(message, dict)
        messages.append(message)

    assert len(messages) == 2


def test_iterable_fitfile_filtered_messages(small_fitfile):
    messages = []

    for message in small_fitfile(message_type="file_id"):
        assert isinstance(message, dict)
        messages.append(message)

    assert len(messages) == 1
    assert messages[0] == {
        "manufacturer": 255,
        "number": 0,
        "product": 0,
        "serial_number": None,
        "time_created": 1046114779,
        "type": 4,
    }


def test_iterable_fitfile_filtered_messages_and_fields(small_fitfile):
    messages = []

    for message in small_fitfile(
        message_type="record", fields=["timestamp", "speed", "power", "heart_rate"]
    ):
        assert isinstance(message, dict)
        messages.append(message)

    assert len(messages) == 1
    assert messages[0] == {
        "heart_rate": 98,
        "power": 121,
        "speed": 3765,
        "timestamp": 1046114799,
    }
