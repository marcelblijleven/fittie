from typing import Optional


class DecodeException(Exception):
    default_detail = "could not decode provided data"
    position: int

    def __init__(self, *, detail: Optional[str], position: int):
        if not detail:
            self.detail = self.default_detail
        else:
            self.detail = detail

        self.position = position

    def __str__(self):
        return f"{self.detail} at position {self.position}"
