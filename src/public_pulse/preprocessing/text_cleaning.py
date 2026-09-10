"""Production text preprocessing for Public Pulse.

This module is a verbatim port of the `clean_text()` function defined and
justified in the authoritative data-preparation notebooks:

    - layer2_01_data_preparation_final.ipynb  (Section 6, cell defining
      clean_text() -- the original)
    - layer4_01_data_preparation_final.ipynb  (Section 6, explicitly
      described as "identical logic to Layer 2's clean_text()")

Both notebooks flag this exact duplication as a known trade-off and name
this file (`src/public_pulse/preprocessing/text_cleaning.py`) as where it
should be extracted to, so training and inference share one definition.
This port does not change a single regex or reorder a single step from
what the notebooks actually run -- see PRESERVATION NOTES below for what
was deliberately verified to carry over unchanged.

------------------------------------------------------------------------
THE PER-LAYER INPUT CONTRACT (do not blur this)
------------------------------------------------------------------------

    Layer 1 (Utility)  -> text_raw    (get_layer1_input(), NO cleaning)
    Layer 2 (Topic)    -> text_clean  (clean_text())
    Layer 4 (Stance)   -> text_clean  (clean_text())

Layer 1's own data-preparation notebook (01_data_preparation.ipynb,
Section 6) explicitly evaluated and REJECTED normalization for Layer 1's
input, specifically because punctuation/casing/emphasis patterns are
plausible spam/noise signal that normalization would erase, and because
that decision "does not bind the Layer 2/Layer 4 notebooks -- each should
make and document this choice independently". Layer 2 and Layer 4 each
independently chose to clean, for a different, narrower reason: Sinhala's
combining-mark variability needs Unicode NFC normalization or the
tokenizer fragments visually-identical text into different token
sequences. Both layers' notebooks explicitly did NOT add lowercasing,
punctuation stripping, or repeated-character collapsing, for the same
signal-preservation reasoning as Layer 1.

Do not add either layer's transformation to the other's function. They
are intentionally different, for documented reasons, not an oversight to
"fix".

------------------------------------------------------------------------
PRESERVATION NOTES -- what was verified before writing this file
------------------------------------------------------------------------

- The three regex patterns and their exact source order (NFC normalize ->
  strip zero-width chars -> URL -> "[URL]" -> collapse whitespace) are
  copied character-for-character from both notebooks' `clean_text()`
  cells, which are byte-identical to each other.
- The non-str-input guard (`return ""`) is copied as-is; it is not a new
  rule invented for production.
- No step here (lowercasing, punctuation/emoji removal, stemming,
  transliteration, translation, repeated-character collapsing) exists in
  either notebook, so none is implemented here. Do not add any of these
  without updating the authoritative notebooks first -- production
  preprocessing must never diverge from what a checkpoint was trained on.
- Real before/after examples from layer2_01_data_preparation_final's own
  executed output are used as golden regression tests in
  tests/test_preprocessing.py, not invented examples.
"""

import re
import unicodedata
from typing import Optional

# Copied verbatim from layer2_01_data_preparation_final.ipynb /
# layer4_01_data_preparation_final.ipynb (identical in both).
ZERO_WIDTH_PATTERN = re.compile(r"[\u200b\u200c\u200d\ufeff]")
WHITESPACE_PATTERN = re.compile(r"\s+")
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")


def clean_text(text: Optional[str]) -> str:
    """Produce the production-equivalent `text_clean` for Layer 2 / Layer 4.

    Verbatim port of the notebooks' `clean_text()`:
        1. Non-str input (including None) -> "" (matches notebook behavior)
        2. Unicode NFC normalization
        3. Zero-width character removal (\\u200b \\u200c \\u200d \\ufeff)
        4. URL replacement with the literal placeholder "[URL]"
        5. Whitespace collapse + strip

    Deliberately does NOT: lowercase, strip punctuation, collapse repeated
    characters, stem, transliterate, or translate. None of these exist in
    the authoritative notebooks' cleaning step.

    This function must produce byte-identical output to the notebooks'
    `clean_text()` for the same input -- see the golden regression tests
    in tests/test_preprocessing.py, which use real RAW/CLEAN pairs taken
    from layer2_01_data_preparation_final.ipynb's own executed output.
    """
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFC", text)
    text = ZERO_WIDTH_PATTERN.sub("", text)
    text = URL_PATTERN.sub("[URL]", text)
    text = WHITESPACE_PATTERN.sub(" ", text).strip()
    return text


def get_layer1_input(text_raw: Optional[str]) -> str:
    """Return Layer 1's model input: the ORIGINAL, unmodified comment text.

    Layer 1 (01_data_preparation.ipynb, Section 6) made an explicit,
    documented decision to use raw text over any normalized variant,
    specifically because punctuation/casing/emphasis patterns are
    plausible signal for distinguishing VALID from NOISE, and because
    normalization introduced null values with no corresponding benefit.

    This function performs NO content transformation -- no NFC
    normalization, no URL replacement, no whitespace collapsing. The only
    thing it does is coerce non-str/None input to "" for null-safety in
    a production pipeline (the same null-safety guard `clean_text()`
    applies for its own non-str case) -- this is a production safety net,
    not a preprocessing rule invented for Layer 1. If you need Layer 2 or
    Layer 4's input, use `clean_text()`, never this function.
    """
    if not isinstance(text_raw, str):
        return ""
    return text_raw


def build_text_variants(text_raw: Optional[str]) -> dict:
    """Build both text variants ETL needs to persist for a single comment.

    Returns {"text_raw": <Layer 1 input>, "text_clean": <Layer 2/4 input>}.
    Both keys are always present and are plain strings (never None), so
    downstream storage/inference code does not need its own null-handling
    for these two fields. This does not implement ETL itself (Phase 7) --
    it only exposes the two model-input variants ETL is expected to call.
    """
    return {
        "text_raw": get_layer1_input(text_raw),
        "text_clean": clean_text(text_raw),
    }
