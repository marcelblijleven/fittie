"""Opt-in processing keeps the default decoding path inexpensive."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecodeOptions:
    apply_scale_and_offset: bool = True
    expand_subfields: bool = True
    expand_components: bool = True
    convert_types_to_strings: bool = False
    convert_datetimes_to_dates: bool = False
    merge_heart_rates: bool = False
    apply_native_overrides: bool = False

    def __post_init__(self):
        if self.apply_native_overrides and not self.apply_scale_and_offset:
            raise ValueError("native overrides require scaled native values")
        if self.merge_heart_rates and not (
            self.apply_scale_and_offset and self.expand_components
        ):
            raise ValueError(
                "heart-rate merging requires scaled values and component expansion"
            )


DEFAULT_OPTIONS = DecodeOptions()
