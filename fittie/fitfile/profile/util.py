import copy

from functools import lru_cache

from fittie.fitfile.profile.message_profile import MessageProfile
from fittie.fitfile.profile.messages import MESSAGES


@lru_cache(maxsize=None)
def get_message_profile(number: int) -> MessageProfile:
    if number not in MESSAGES:
        raise ValueError(f'unknown message number "{number}"')

    raw = copy.deepcopy(MESSAGES[number])

    raw["fields"]: dict[int, MessageProfile.FieldProfile] = {
        k: MessageProfile.FieldProfile(**v) for k, v in raw["fields"].items()
    }

    return MessageProfile(**raw)
