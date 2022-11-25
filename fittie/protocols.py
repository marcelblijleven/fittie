from typing import BinaryIO, Protocol, TypeVar


class Encodable(Protocol):
    def encode(self) -> bytes:
        ...


class Decodable(Protocol):
    @classmethod
    def decode(cls, data: BinaryIO):
        ...

    @classmethod
    def from_data(cls, data: BinaryIO):
        ...


class Codable(Encodable, Decodable, Protocol):
    ...
