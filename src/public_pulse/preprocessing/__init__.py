"""Production text preprocessing -- see text_cleaning.py for the
authoritative per-layer input contract (Layer 1: text_raw, Layer 2/4:
text_clean), ported verbatim from the data-preparation notebooks.
"""

from public_pulse.preprocessing.text_cleaning import (
    build_text_variants,
    clean_text,
    get_layer1_input,
)
from public_pulse.preprocessing.validators import (
    TextContractError,
    assert_layer2_or_layer4_input_is_clean,
    assert_not_already_cleaned,
    looks_like_cleaned_text,
)

__all__ = [
    "clean_text",
    "get_layer1_input",
    "build_text_variants",
    "TextContractError",
    "assert_not_already_cleaned",
    "assert_layer2_or_layer4_input_is_clean",
    "looks_like_cleaned_text",
]
