"""Runs the active 3-layer cascade: layer1 -> layer2 -> layer4.

Layer 3 was removed as a documented research-scope decision and is not
part of this cascade (see docs/taxonomy.md). Loads all three checkpoints
once per InferenceCascade instance and reuses them across every
predict()/predict_batch() call. Early-exit on Layer 1 NOISE: Layer 2 and
Layer 4 are never invoked for a NOISE comment -- not just discarded
afterward, but never called at all (see predict_batch()'s valid_indices
guard). Layer 1 has no SPAM class -- NOISE is the only non-VALID label
and the only early-exit trigger.
"""

from typing import List

from public_pulse.models.factory import build_all_classifiers
from public_pulse.models.results import CascadeResult
from public_pulse.preprocessing.text_cleaning import build_text_variants


class InferenceCascade:
    def __init__(self, layer1, layer2, layer4):
        """Dependency-injected constructor -- accepts anything implementing
        BaseClassifier's `predict_batch(texts) -> list[LayerPrediction]`
        interface. Production code should normally use `from_config()`;
        tests inject fakes/mocks here directly (see tests/test_cascade.py).
        """
        self.layer1 = layer1
        self.layer2 = layer2
        self.layer4 = layer4

    @classmethod
    def from_config(cls) -> "InferenceCascade":
        """Production convenience constructor: builds all three real
        classifiers from configs/layerN.yaml (see models/factory.py).
        Construction always succeeds; actual model loading is deferred
        until the first predict() call, and will raise
        CheckpointNotFoundError given this repository's current Phase 2
        status (checkpoints are ACCESS_UNAVAILABLE from this environment).
        """
        classifiers = build_all_classifiers()
        return cls(classifiers["layer1"], classifiers["layer2"], classifiers["layer4"])

    def predict(self, text_raw: str) -> CascadeResult:
        return self.predict_batch([text_raw])[0]

    def predict_batch(self, texts_raw: List[str]) -> List[CascadeResult]:
        if not texts_raw:
            return []

        variants = [build_text_variants(t) for t in texts_raw]
        raw_inputs = [v["text_raw"] for v in variants]
        clean_inputs = [v["text_clean"] for v in variants]

        layer1_predictions = self.layer1.predict_batch(raw_inputs)

        # Indices of comments Layer 1 did NOT classify as NOISE. Layer 2
        # and Layer 4 are called with exactly this subset -- if it is
        # empty (an all-NOISE batch), layer2/layer4 are not called at all.
        valid_indices = [i for i, pred in enumerate(layer1_predictions) if pred.label != "NOISE"]

        layer2_by_index = {}
        layer4_by_index = {}
        if valid_indices:
            valid_clean_texts = [clean_inputs[i] for i in valid_indices]
            layer2_predictions = self.layer2.predict_batch(valid_clean_texts)
            layer4_predictions = self.layer4.predict_batch(valid_clean_texts)
            for original_index, l2_pred, l4_pred in zip(valid_indices, layer2_predictions, layer4_predictions):
                layer2_by_index[original_index] = l2_pred
                layer4_by_index[original_index] = l4_pred

        return [
            CascadeResult(
                text_raw=raw_inputs[i],
                text_clean=clean_inputs[i],
                layer1=layer1_predictions[i],
                layer2=layer2_by_index.get(i),
                layer4=layer4_by_index.get(i),
            )
            for i in range(len(texts_raw))
        ]
