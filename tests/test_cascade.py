"""Cascade routing/control-flow tests (Phase 4).

Everything in this file uses FakeClassifier, a test-only double defined
below. FakeClassifier is NOT a model, has no relationship to the real
Layer 1/2/4 checkpoints, and its "confidence" values are arbitrary
constants chosen for test readability -- nothing here should ever be
read as validating real model behavior or output quality. It exists
solely to make the cascade's ROUTING logic (early-exit on NOISE,
raw-vs-clean text separation, batching, load-once-per-instance reuse)
independently testable without a real checkpoint, which per Phase 2
remains ACCESS_UNAVAILABLE in this environment.
"""

from public_pulse.inference.cascade import InferenceCascade
from public_pulse.models import CheckpointNotFoundError
from public_pulse.models.results import LayerPrediction
import pytest

class FakeClassifier:
    """Minimal stand-in for BaseClassifier's public interface.

    Records every batch of texts it is called with (`call_log`), so tests
    can assert exactly what a layer did and did not receive -- this is
    how "Layer 2/4 never invoked for a NOISE result" and "Layer 1 gets
    text_raw, Layer 2/4 get text_clean" are verified precisely, rather
    than inferred from output alone.
    """

    def __init__(self, layer_name: str, label_for_text=None, default_label="VALID", default_label_id=0):
        self.layer_name = layer_name
        self.call_log = []  # list of batches (each a list[str]) predict_batch was called with
        self._loaded = False
        self.load_count = 0
        self._label_for_text = label_for_text or {}
        self._default_label = default_label
        self._default_label_id = default_label_id

    def load(self):
        if self._loaded:
            return
        self._loaded = True
        self.load_count += 1

    def predict_batch(self, texts):
        self.load()
        self.call_log.append(list(texts))
        results = []
        for text in texts:
            label = self._label_for_text.get(text, self._default_label)
            results.append(
                LayerPrediction(
                    layer=self.layer_name,
                    label=label,
                    label_id=self._default_label_id,
                    confidence=0.99,  # arbitrary test constant, not a real model output
                    model_version="fake-test-double-not-a-real-model",
                )
            )
        return results

    def predict(self, text):
        return self.predict_batch([text])[0]


def make_cascade(layer1_labels=None, layer1_default="VALID"):
    layer1 = FakeClassifier("layer1", label_for_text=layer1_labels, default_label=layer1_default)
    layer2 = FakeClassifier("layer2", default_label="TOPIC_GOV")
    layer4 = FakeClassifier("layer4", default_label="STANCE_CRIT")
    cascade = InferenceCascade(layer1, layer2, layer4)
    return cascade, layer1, layer2, layer4


class TestValidPathRunsAllThreeLayers:
    def test_layer1_valid_triggers_layer2_and_layer4(self):
        cascade, layer1, layer2, layer4 = make_cascade(layer1_default="VALID")
        result = cascade.predict("some comment")
        assert result.layer1.label == "VALID"
        assert result.layer2 is not None
        assert result.layer4 is not None
        assert result.layer2.label == "TOPIC_GOV"
        assert result.layer4.label == "STANCE_CRIT"


class TestNoiseEarlyExit:
    def test_layer1_noise_result_has_no_layer2_or_layer4(self):
        cascade, layer1, layer2, layer4 = make_cascade(layer1_default="NOISE")
        result = cascade.predict("spammy comment")
        assert result.layer1.label == "NOISE"
        assert result.layer2 is None
        assert result.layer4 is None

    def test_layer2_is_never_called_for_a_noise_comment(self):
        cascade, layer1, layer2, layer4 = make_cascade(layer1_default="NOISE")
        cascade.predict("spammy comment")
        assert layer2.call_log == []  # never invoked, not just result discarded

    def test_layer4_is_never_called_for_a_noise_comment(self):
        cascade, layer1, layer2, layer4 = make_cascade(layer1_default="NOISE")
        cascade.predict("spammy comment")
        assert layer4.call_log == []

    def test_mixed_batch_only_calls_layer2_and_layer4_for_valid_subset(self):
        texts = ["noise one", "valid one", "noise two", "valid two"]
        labels = {"noise one": "NOISE", "valid one": "VALID", "noise two": "NOISE", "valid two": "VALID"}
        cascade, layer1, layer2, layer4 = make_cascade(layer1_labels=labels)
        results = cascade.predict_batch(texts)

        assert [r.layer1.label for r in results] == ["NOISE", "VALID", "NOISE", "VALID"]
        assert results[0].layer2 is None and results[0].layer4 is None
        assert results[2].layer2 is None and results[2].layer4 is None
        assert results[1].layer2 is not None and results[1].layer4 is not None
        assert results[3].layer2 is not None and results[3].layer4 is not None

        # Layer 2/4 must only ever have seen the two VALID comments' clean text.
        assert len(layer2.call_log) == 1
        assert len(layer2.call_log[0]) == 2
        assert len(layer4.call_log[0]) == 2

    def test_all_noise_batch_never_calls_layer2_or_layer4_at_all(self):
        texts = ["noise a", "noise b", "noise c"]
        cascade, layer1, layer2, layer4 = make_cascade(layer1_default="NOISE")
        cascade.predict_batch(texts)
        assert layer2.call_log == []
        assert layer4.call_log == []
        # Since predict_batch guards on an empty valid_indices list, the
        # layers are never loaded either -- not just "called with nothing".
        assert layer2.load_count == 0
        assert layer4.load_count == 0


class TestRawVsCleanInputSeparation:
    def test_layer1_receives_unmodified_raw_text(self):
        raw = "  Weird   spacing AND CAPS https://x.com  "
        cascade, layer1, layer2, layer4 = make_cascade()
        cascade.predict(raw)
        assert layer1.call_log == [[raw]]  # byte-for-byte, no transformation

    def test_layer2_receives_cleaned_text_not_raw(self):
        raw = "  Weird   spacing https://x.com  "
        cascade, layer1, layer2, layer4 = make_cascade()
        cascade.predict(raw)
        assert layer2.call_log == [["Weird spacing [URL]"]]

    def test_layer4_receives_the_same_cleaned_text_as_layer2(self):
        raw = "  Weird   spacing https://x.com  "
        cascade, layer1, layer2, layer4 = make_cascade()
        cascade.predict(raw)
        assert layer2.call_log == layer4.call_log

    def test_cascade_result_exposes_both_text_variants(self):
        raw = "  spaced   text  "
        cascade, *_ = make_cascade()
        result = cascade.predict(raw)
        assert result.text_raw == raw
        assert result.text_clean == "spaced text"


class TestLabelDecodingAndStructure:
    def test_result_to_dict_shape_matches_conceptual_contract(self):
        cascade, *_ = make_cascade(layer1_default="VALID")
        result = cascade.predict("a comment")
        as_dict = result.to_dict()
        assert set(as_dict.keys()) == {"text_raw", "text_clean", "layer1", "layer2", "layer4"}
        assert set(as_dict["layer1"].keys()) == {"label", "label_id", "confidence", "model_version"}

    def test_noise_result_to_dict_has_null_layer2_and_layer4(self):
        cascade, *_ = make_cascade(layer1_default="NOISE")
        result = cascade.predict("spam")
        as_dict = result.to_dict()
        assert as_dict["layer2"] is None
        assert as_dict["layer4"] is None

    def test_is_noise_property(self):
        cascade_noise, *_ = make_cascade(layer1_default="NOISE")
        cascade_valid, *_ = make_cascade(layer1_default="VALID")
        assert cascade_noise.predict("x").is_noise is True
        assert cascade_valid.predict("x").is_noise is False


class TestBatchInference:
    def test_predict_batch_returns_results_in_original_order(self):
        texts = ["first", "second", "third"]
        cascade, *_ = make_cascade()
        results = cascade.predict_batch(texts)
        assert [r.text_raw for r in results] == texts

    def test_empty_batch_returns_empty_list_without_calling_any_layer(self):
        cascade, layer1, layer2, layer4 = make_cascade()
        results = cascade.predict_batch([])
        assert results == []
        assert layer1.call_log == []
        assert layer2.call_log == []
        assert layer4.call_log == []


class TestModelsLoadedOnceAcrossMultiplePredictions:
    def test_repeated_predict_calls_do_not_reload_any_layer(self):
        cascade, layer1, layer2, layer4 = make_cascade(layer1_default="VALID")
        cascade.predict("first comment")
        cascade.predict("second comment")
        cascade.predict("third comment")
        # Three predictions, but each classifier's own idempotent load()
        # guard means load_count reflects "loaded", not "loaded per call".
        assert layer1.load_count == 1
        assert layer2.load_count == 1
        assert layer4.load_count == 1
        # And it really was called three separate times, not batched implicitly:
        assert len(layer1.call_log) == 3


class TestFromConfigConstructorBuildsRealClassifiers:
    def test_from_config_produces_an_inference_cascade_instance(self):
        # Construction only -- does not call predict()/load(), so this
        # succeeds even though real checkpoints remain ACCESS_UNAVAILABLE.
        cascade = InferenceCascade.from_config()
        assert isinstance(cascade, InferenceCascade)
        assert cascade.layer1.LAYER_NAME == "layer1"
        assert cascade.layer2.LAYER_NAME == "layer2"
        assert cascade.layer4.LAYER_NAME == "layer4"

    def test_from_config_cascade_predict_succeeds_with_real_checkpoints(self):
        cascade = InferenceCascade.from_config()
        res = cascade.predict("කොහොමද")
        assert res.layer1.label in ("VALID", "NOISE")

