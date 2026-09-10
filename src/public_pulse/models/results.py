"""Typed result structures for model predictions and cascade output.

Plain dataclasses -- the repository's existing scaffold doesn't use
Pydantic outside `api/schemas/`, and there is no FastAPI boundary at this
layer (Phase 4 is model integration, not API), so dataclasses are the
non-overengineered choice here per the Phase 4 instructions.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LayerPrediction:
    """A single layer's prediction for a single piece of text.

    `model_version` is only ever populated from real metadata actually
    read alongside the checkpoint (e.g. a training_metadata.json field or
    a config-declared version string) -- never invented. It is `None`
    whenever no such metadata was available to read, which is expected
    and correct for as long as checkpoints remain ACCESS_UNAVAILABLE.
    """

    layer: str  # "layer1" | "layer2" | "layer4"
    label: str
    label_id: int
    confidence: float
    model_version: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "label_id": self.label_id,
            "confidence": self.confidence,
            "model_version": self.model_version,
        }


@dataclass(frozen=True)
class CascadeResult:
    """Full cascade output for a single comment.

    `layer2` and `layer4` are None whenever Layer 1 predicted NOISE --
    this is the terminal, early-exit case, and the cascade must never
    have invoked Layer 2 or Layer 4 to produce it.
    """

    text_raw: str
    text_clean: str
    layer1: LayerPrediction
    layer2: Optional[LayerPrediction]
    layer4: Optional[LayerPrediction]

    @property
    def is_noise(self) -> bool:
        return self.layer1.label == "NOISE"

    def to_dict(self) -> dict:
        return {
            "text_raw": self.text_raw,
            "text_clean": self.text_clean,
            "layer1": self.layer1.to_dict(),
            "layer2": self.layer2.to_dict() if self.layer2 else None,
            "layer4": self.layer4.to_dict() if self.layer4 else None,
        }
