"""A small mutable mapping sharing developer identities across a definition."""

from collections.abc import Iterator, MutableMapping
from typing import Any


class DeveloperValues(MutableMapping[tuple[int, int], Any]):
    __slots__ = ("_keys", "_values")

    def __init__(self, keys: tuple[tuple[int, int], ...], values: list[Any]):
        self._keys = keys
        # Single-field contributors are common; avoid a retained list per record.
        self._values = values[0] if len(keys) == 1 else values

    def _index(self, key: tuple[int, int]) -> int:
        try:
            return self._keys.index(key)
        except ValueError:
            raise KeyError(key) from None

    def __getitem__(self, key: tuple[int, int]) -> Any:
        index = self._index(key)
        return self._values if len(self._keys) == 1 else self._values[index]

    def __setitem__(self, key: tuple[int, int], value: Any) -> None:
        try:
            index = self._keys.index(key)
        except ValueError:
            if len(self._keys) == 1:
                self._values = [self._values]
            self._keys += (key,)
            self._values.append(value)
            if len(self._keys) == 1:
                self._values = value
        else:
            if len(self._keys) == 1:
                self._values = value
            else:
                self._values[index] = value

    def __delitem__(self, key: tuple[int, int]) -> None:
        index = self._index(key)
        if len(self._keys) == 1:
            self._values = []
        else:
            del self._values[index]
            if len(self._keys) == 2:
                self._values = self._values[0]
        self._keys = self._keys[:index] + self._keys[index + 1 :]

    def __iter__(self) -> Iterator[tuple[int, int]]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def __repr__(self) -> str:
        return repr(dict(self.items()))
