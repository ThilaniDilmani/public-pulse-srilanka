"""Shared base classifier contract used by the three active layer models
(Layer 1, Layer 2, Layer 4 -- the numbering is intentional, not a typo;
Layer 3 was removed as a documented research-scope decision; see
docs/taxonomy.md).

Design notes:

- torch/transformers are imported LAZILY, inside `load()`, not at module
  import time. This lets the rest of the codebase (and its tests) import
  `public_pulse.models`/`public_pulse.inference` without requiring those
  heavy frameworks to be installed -- relevant right now because this
  development environment does not have them installed, and because
  Phase 2 established that no real checkpoint is accessible here anyway,
  so there is nothing a real load could succeed against yet.
- Checkpoint loading distinguishes three failure modes on purpose (see
  models/exceptions.py): a missing Python dependency, a missing
  checkpoint path, and a loaded-but-invalid artifact. Callers (and
  tests) should never have to guess which occurred from an error string.
- A model is loaded at most once per classifier instance. `load()` is
  idempotent; `predict()`/`predict_batch()` call it internally so callers
  don't need to remember to.
"""

from pathlib import Path
from typing import List, Optional

from public_pulse.labels.label_map import LabelMap
from public_pulse.models.exceptions import (
    CheckpointNotFoundError,
    MissingDependencyError,
    ModelLoadError,
)
from public_pulse.models.results import LayerPrediction


class BaseClassifier:
    """Not meant to be instantiated directly -- subclasses (Layer1Classifier
    etc.) set LAYER_NAME. Everything else is shared.
    """

    LAYER_NAME: str = "unknown_layer"

    def __init__(
        self,
        checkpoint_path: str,
        label_map_path: str,
        max_seq_length: int = 256,
        device: Optional[str] = None,
        model_version: Optional[str] = None,
    ):
        self.checkpoint_path = Path(checkpoint_path)
        self.label_map = LabelMap(label_map_path)
        self.max_seq_length = max_seq_length
        self.model_version = model_version  # never invented -- see results.py

        self._device_preference = device  # None => auto-detect at load time
        self._model = None
        self._tokenizer = None
        self._device = None
        self._torch = None  # stashed module reference, set once loaded
        self.load_count = 0  # exposed for tests verifying "loaded once"

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """Load the tokenizer + model from `self.checkpoint_path`.

        Idempotent: calling this on an already-loaded classifier does
        nothing (does not reload, does not re-touch disk). This is what
        guarantees the model is loaded once and reused across many
        predict() calls.
        """
        if self.is_loaded:
            return

        if not self.checkpoint_path.exists():
            raise CheckpointNotFoundError(
                f"[{self.LAYER_NAME}] No checkpoint found at '{self.checkpoint_path}'. "
                "This is a configuration/deployment problem, not a code problem -- "
                "per Phase 2, this repository's checkpoints are reported to exist "
                "on Google Drive but are not accessible from this environment. "
                "Set the appropriate checkpoint path (see configs/layerN.yaml and "
                "its environment-variable override) to a real, locally accessible "
                "checkpoint directory before calling predict()."
            )

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise MissingDependencyError(
                f"[{self.LAYER_NAME}] torch/transformers are not installed in this "
                "environment. Install them (see pyproject.toml) before loading any "
                "model. This is an environment problem, not a checkpoint problem -- "
                f"a checkpoint was found at '{self.checkpoint_path}', but it cannot "
                "be loaded without these packages."
            ) from exc

        try:
            tokenizer = AutoTokenizer.from_pretrained(str(self.checkpoint_path))
            model = AutoModelForSequenceClassification.from_pretrained(str(self.checkpoint_path))
        except Exception as exc:
            raise ModelLoadError(
                f"[{self.LAYER_NAME}] Found a checkpoint at '{self.checkpoint_path}' "
                f"but failed to load it as a sequence classification model: {exc}"
            ) from exc

        expected_num_labels = len(self.label_map.label_to_id)
        actual_num_labels = getattr(model.config, "num_labels", None)
        if actual_num_labels != expected_num_labels:
            raise ModelLoadError(
                f"[{self.LAYER_NAME}] Checkpoint at '{self.checkpoint_path}' has "
                f"{actual_num_labels} output labels, but this layer's label_map "
                f"({self.label_map.path}) defines {expected_num_labels}. Refusing "
                "to use a model whose output head does not match the expected "
                "taxonomy -- this would silently corrupt every prediction."
            )

        device_str = self._device_preference or ("cuda" if torch.cuda.is_available() else "cpu")
        device = torch.device(device_str)
        model.to(device)
        model.eval()

        self._torch = torch
        self._tokenizer = tokenizer
        self._model = model
        self._device = device
        self.load_count += 1

    def predict(self, text: str) -> LayerPrediction:
        return self.predict_batch([text])[0]

    def predict_batch(self, texts: List[str]) -> List[LayerPrediction]:
        self.load()  # no-op if already loaded
        torch = self._torch

        encoded = self._tokenizer(
            texts,
            truncation=True,
            padding=True,  # dynamic padding, consistent with training config
            max_length=self.max_seq_length,
            return_tensors="pt",
        ).to(self._device)

        with torch.no_grad():
            outputs = self._model(**encoded)
            probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)

        predictions = []
        for row in probabilities:
            confidence, label_id_tensor = torch.max(row, dim=-1)
            label_id = int(label_id_tensor.item())
            label = self.label_map.id_to_label[label_id]
            predictions.append(
                LayerPrediction(
                    layer=self.LAYER_NAME,
                    label=label,
                    label_id=label_id,
                    confidence=float(confidence.item()),
                    model_version=self.model_version,
                )
            )
        return predictions
