from abc import ABC, abstractmethod


class IterableMixin(ABC):
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

    def __next__(self):
        if self._iter_index >= len(self._iter_collection):
            # Remove _iter_collection value from cache, if it exists.
            # If _iter_collection is cached, then it should exist and be cleared
            # as soon as the collection has been fully iterated.
            if "_iter_collection" in self.__dict__:
                del self.__dict__["_iter_collection"]

            raise StopIteration

        value = self._iter_collection[self._iter_index]
        self._iter_index += 1
        return value

    def __iter__(self):
        self._iter_index = 0
        return self
