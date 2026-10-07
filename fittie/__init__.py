from .fitfile.decode import decode, iter_files, iter_messages
from .fitfile.encode import Encoder, encode
from .fitfile.options import DecodeOptions
from .fitfile.validation import ValidationIssue, validate
from .profile.version import PROFILE_VERSION

__all__ = [
    "decode",
    "encode",
    "Encoder",
    "DecodeOptions",
    "iter_files",
    "iter_messages",
    "validate",
    "ValidationIssue",
]
__VERSION__ = "1.0.0"
__PROFILE_VERSION__ = PROFILE_VERSION
