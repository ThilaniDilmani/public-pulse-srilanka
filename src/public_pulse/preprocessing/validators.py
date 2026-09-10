"""Guards enforcing the per-layer text-input contract.

Layer 1 must receive `text_raw` (unmodified). Layer 2 and Layer 4 must
receive `text_clean` (see text_cleaning.py for what that means and why).
These are small, deliberately dumb runtime checks -- their only job is to
make it loud and immediate if inference code (Phase 4) is ever wired up
backwards, e.g. accidentally passing cleaned text into Layer 1.

This module has no model/torch/transformers dependency and is safe to
import and test without any ML framework installed.
"""

from public_pulse.preprocessing.text_cleaning import clean_text


class TextContractError(ValueError):
    """Raised when text handed to a layer does not match its input contract."""


def looks_like_cleaned_text(text_raw_candidate: str) -> bool:
    """Heuristic: would cleaning this text change it?

    If `clean_text(text)` differs from `text`, then `text` was not the
    original raw value -- either it was already cleaned, or it contains
    something cleaning would alter (a zero-width character, a raw URL,
    non-NFC Unicode, or irregular whitespace). This is a heuristic, not a
    proof: a raw comment that happens to already be in canonical NFC form
    with no zero-width chars, no URLs, and single-spaced whitespace is
    indistinguishable from cleaned text, and that's fine -- there is
    nothing to guard against in that case since the two variants are
    identical anyway.
    """
    return clean_text(text_raw_candidate) != text_raw_candidate


def assert_not_already_cleaned(text_raw: str, candidate_layer1_input: str) -> None:
    """Guard: fail loudly if Layer 1 is about to receive text_clean instead of text_raw.

    Call this at the Layer 1 call site with both the known-original
    `text_raw` and whatever value is about to be passed to the model.
    They must be identical -- Layer 1 performs zero transformation.
    """
    if candidate_layer1_input != text_raw:
        raise TextContractError(
            "Layer 1 must receive text_raw unmodified. The value about to be "
            "passed to Layer 1 does not match the original text_raw -- this "
            "usually means clean_text() (or some other transformation) was "
            "applied before calling Layer 1, which it must never be."
        )


def assert_layer2_or_layer4_input_is_clean(text_raw: str, candidate_input: str) -> None:
    """Guard: fail loudly if Layer 2/4 is about to receive unclean text_raw.

    Call this at the Layer 2 or Layer 4 call site with the original
    `text_raw` and whatever value is about to be passed to the model.
    The candidate must equal `clean_text(text_raw)`.
    """
    expected = clean_text(text_raw)
    if candidate_input != expected:
        raise TextContractError(
            "Layer 2/Layer 4 must receive text_clean (clean_text(text_raw)). "
            "The value about to be passed does not match -- this usually "
            "means text_raw was passed through unmodified, or a different "
            "cleaning function was used."
        )
