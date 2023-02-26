from unittest import mock
from functools import cached_property

from fittie.utils.iterable import IterableMixin


class Foo(IterableMixin):
    lst: list

    def __init__(self, lst):
        self.lst = lst

    @property
    def _iter_collection(self):
        return self.lst


def compute() -> list:
    return [1, 2, 3, 4, 5]


class FooCached(IterableMixin):
    @cached_property
    def _iter_collection(self):
        return compute()


def test_iterable_non_cached_property():
    lst = [1, 2, 3, 4, 5]
    foo = Foo(lst)

    for idx, value in enumerate(foo):
        assert value == lst[idx]


def test_iterable_cached_property():
    foo = FooCached()
    lst = [1, 2, 3, 4, 5]

    with mock.patch(
        "tests.fittie.utils.test_iterable.compute", return_value=lst
    ) as mock_compute:
        for idx, value in enumerate(foo):
            assert value == lst[idx]

        mock_compute.assert_called_once()

    for idx, value in enumerate(foo):
        assert value == lst[idx]
