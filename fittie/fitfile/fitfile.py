from __future__ import annotations
from typing import BinaryIO

from fittie.fitfile.records import DefinitionMessage


class FitFile:
    definitions: dict[int, DefinitionMessage]

    def __init__(self):
        self.definitions = {}

    @staticmethod
    def from_file(file: BinaryIO) -> FitFile:
        ...
