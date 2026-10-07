"""FIT strings are NUL terminated UTF-8; repeated strings share one field."""


def decode_string(value: bytes) -> str | list[str] | None:
    value = value.rstrip(b"\x00")
    if not value:
        return None
    parts = value.decode("utf-8", errors="replace").split("\x00")
    return parts[0] if len(parts) == 1 else parts
