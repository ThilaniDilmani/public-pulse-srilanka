"""Preprocessing tests (Phase 3).

No torch/transformers/model-checkpoint/GPU dependency anywhere in this
file -- these tests exercise pure-Python text transformation only, per
the Phase 3 requirement that preprocessing be verifiable independently
of any ML framework.
"""

import pytest

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


# ---------------------------------------------------------------------------
# Golden regression cases -- real RAW/CLEAN pairs taken verbatim from
# layer2_01_data_preparation_final.ipynb's own executed output (cell
# printing `changed.sample(4, random_state=RANDOM_STATE)`), not invented.
# Layer 4's notebook uses the byte-identical clean_text() (confirmed by
# direct comparison of both notebooks' source cells), so these cases are
# valid regression coverage for both layers' shared cleaning function.
# ---------------------------------------------------------------------------

GOLDEN_CASES = [
    (
        "ඇය කියන්නේ  සෑම රජයේ ආයතනයකම මගේ පොටෝ\r\nඑක ගහන්න එපා😮 මම එතන හිතුවා",
        "ඇය කියන්නේ සෑම රජයේ ආයතනයකම මගේ පොටෝ එක ගහන්න එපා😮 මම එතන හිතුවා",
    ),
    (
        ", ජංගි අරගල කරලා IMF ගෙනාවා, රනිල් AKD ජනපති කලා, ආර්ථිකය, ජාතික ආරක්ෂ",
        ", ජංගි අරගල කරලා IMF ගෙනාවා, රනිල් AKD ජනපති කලා, ආර්ථිකය, ජාතික ආරක්ෂ",
    ),
    (
        "Dama ඝාතක sataka නිකායේ  saga සමුළුව 😂😂😂😂😂",
        "Dama ඝාතක sataka නිකායේ saga සමුළුව 😂😂😂😂😂",
    ),
    (
        "මෙහෙම කියන්න ඔයත් පළාත් සබා අපේක්ෂකයෙක් වෙන්න ඕන . උන්ට ඇර මේ රටේ කාටව",
        "මෙහෙම කියන්න ඔයත් පළාත් සබා අපේක්ෂකයෙක් වෙන්න ඕන . උන්ට ඇර මේ රටේ කාටව",
    ),
]


class TestGoldenRegressionCases:
    @pytest.mark.parametrize("raw,expected_clean", GOLDEN_CASES)
    def test_matches_notebook_executed_output_exactly(self, raw, expected_clean):
        assert clean_text(raw) == expected_clean


# ---------------------------------------------------------------------------
# Per-requirement coverage (Phase 3 instructions, items 1-12)
# ---------------------------------------------------------------------------

class TestCleanTextByLanguageAndContent:
    def test_english_text_unchanged_when_already_canonical(self):
        text = "This is a normal English comment."
        assert clean_text(text) == text

    def test_sinhala_text_preserved_not_transliterated(self):
        text = "අද කාලගුණය ගැන කතා කරමු"
        result = clean_text(text)
        # Content must survive intact -- no transliteration, no character loss.
        assert result == text
        assert all(ch in result for ch in "අදකාලගුණයගැනකතාකරමු")

    def test_singlish_text_preserved(self):
        text = "mama ada office yanna one"
        assert clean_text(text) == text

    def test_sinhala_english_code_mixed_preserved(self):
        text = "meka hariම fake news 😡 share karanna epa"
        result = clean_text(text)
        assert "meka" in result and "fake news" in result and "😡" in result
        assert "ම" in result  # Sinhala character embedded mid-word preserved

    def test_punctuation_not_stripped(self):
        text = "What?! Really... this is unacceptable!!!"
        assert clean_text(text) == text

    def test_repeated_punctuation_not_collapsed(self):
        # Explicitly NOT collapsed -- notebooks treat repeated punctuation
        # as plausible spam/emphasis signal, not noise to remove.
        text = "wow!!!!!! amazing????"
        assert clean_text(text) == text

    def test_emojis_preserved_not_removed(self):
        text = "great job 👏👏👏 keep it up 🔥"
        assert clean_text(text) == text

    def test_repeated_whitespace_collapsed(self):
        text = "too    many     spaces"
        assert clean_text(text) == "too many spaces"

    def test_newlines_and_tabs_collapsed_to_single_space(self):
        text = "line one\n\nline two\t\ttabbed"
        assert clean_text(text) == "line one line two tabbed"

    def test_leading_trailing_whitespace_stripped(self):
        text = "   surrounded by spaces   "
        assert clean_text(text) == "surrounded by spaces"

    def test_url_replaced_with_placeholder(self):
        text = "check this out https://example.com/path?x=1 amazing"
        assert clean_text(text) == "check this out [URL] amazing"

    def test_www_style_url_replaced(self):
        text = "see www.example.com for details"
        assert clean_text(text) == "see [URL] for details"

    def test_multiple_urls_both_replaced(self):
        text = "https://a.com and https://b.com/page"
        assert clean_text(text) == "[URL] and [URL]"

    def test_mentions_and_hashtags_preserved(self):
        # Not addressed by the notebooks' clean_text() -- no removal step
        # exists for @mentions or #hashtags, so they must pass through.
        text = "great point @someone #SriLanka #politics"
        assert clean_text(text) == text

    def test_zero_width_characters_removed(self):
        text = "hid\u200bden\u200czero\u200dwidth\ufeffchars"
        assert clean_text(text) == "hiddenzerowidthchars"

    def test_nfc_normalization_applied(self):
        import unicodedata
        # NFD form (decomposed) vs NFC form (composed) of the same visible text.
        nfd_text = unicodedata.normalize("NFD", "café")
        result = clean_text(nfd_text)
        assert result == unicodedata.normalize("NFC", "café")

    def test_no_lowercasing(self):
        text = "This HAS Mixed CaSe"
        assert clean_text(text) == text

    def test_no_stemming_or_lemmatization(self):
        text = "running runs ran runner"
        assert clean_text(text) == text

    def test_very_long_text_handled(self):
        text = "word " * 5000
        result = clean_text(text)
        assert result == "word " * 4999 + "word"  # collapsed internal spaces, stripped


class TestNullAndEmptyHandling:
    def test_empty_string_returns_empty_string(self):
        assert clean_text("") == ""

    def test_none_returns_empty_string(self):
        assert clean_text(None) == ""

    def test_non_string_input_returns_empty_string(self):
        assert clean_text(12345) == ""
        assert clean_text(["not", "a", "string"]) == ""

    def test_whitespace_only_string_becomes_empty(self):
        assert clean_text("     ") == ""


# ---------------------------------------------------------------------------
# Layer 1 raw-input preservation
# ---------------------------------------------------------------------------

class TestLayer1RawInputPreservation:
    def test_layer1_input_is_completely_unmodified(self):
        text = "  Weird   spacing\n\nAND CAPS!!! 😮 https://x.com  "
        assert get_layer1_input(text) == text  # byte-for-byte, no transformation at all

    def test_layer1_input_differs_from_clean_text_when_cleaning_would_change_it(self):
        text = "raw   text  with   spacing"
        assert get_layer1_input(text) != clean_text(text)
        assert get_layer1_input(text) == text

    def test_layer1_none_input_becomes_empty_string_null_safety_only(self):
        assert get_layer1_input(None) == ""

    def test_layer1_never_receives_clean_text_guard_passes_for_correct_usage(self):
        text_raw = "  double   spaced raw text  "
        layer1_input = get_layer1_input(text_raw)
        assert_not_already_cleaned(text_raw, layer1_input)  # must not raise

    def test_layer1_guard_raises_if_cleaned_text_passed_by_mistake(self):
        text_raw = "  double   spaced raw text  "
        wrong_input = clean_text(text_raw)  # simulates the exact mistake to prevent
        with pytest.raises(TextContractError):
            assert_not_already_cleaned(text_raw, wrong_input)


# ---------------------------------------------------------------------------
# Layer 2 / Layer 4 cleaned-input behavior + contract guard
# ---------------------------------------------------------------------------

class TestLayer2Layer4CleanedInput:
    def test_layer2_and_layer4_use_identical_cleaning_function(self):
        # Both layers' notebooks use the byte-identical clean_text() --
        # there is exactly one function in production, not two.
        text = "  shared  cleaning\r\nlogic https://x.com "
        assert clean_text(text) == "shared cleaning logic [URL]"

    def test_guard_passes_for_correctly_cleaned_input(self):
        text_raw = "  needs   cleaning\n"
        candidate = clean_text(text_raw)
        assert_layer2_or_layer4_input_is_clean(text_raw, candidate)  # must not raise

    def test_guard_raises_if_raw_text_passed_by_mistake(self):
        text_raw = "  needs   cleaning\n"
        with pytest.raises(TextContractError):
            assert_layer2_or_layer4_input_is_clean(text_raw, text_raw)  # raw, not cleaned


class TestLooksLikeCleanedTextHeuristic:
    def test_true_when_cleaning_would_change_input(self):
        assert looks_like_cleaned_text("has   irregular   spacing") is True

    def test_false_when_already_in_canonical_form(self):
        assert looks_like_cleaned_text("already canonical text") is False


# ---------------------------------------------------------------------------
# build_text_variants() -- the ETL-facing entry point
# ---------------------------------------------------------------------------

class TestBuildTextVariants:
    def test_returns_both_variants(self):
        result = build_text_variants("  raw   text https://x.com ")
        assert result == {
            "text_raw": "  raw   text https://x.com ",
            "text_clean": "raw text [URL]",
        }

    def test_never_returns_none_for_either_key(self):
        result = build_text_variants(None)
        assert result["text_raw"] == ""
        assert result["text_clean"] == ""

    def test_deterministic_across_repeated_calls(self):
        text = "Sinhala සිංහල mixed with English 😊 https://a.com"
        first = build_text_variants(text)
        second = build_text_variants(text)
        assert first == second
