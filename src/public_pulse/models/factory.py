"""Builds Layer1Classifier/Layer2Classifier/Layer4Classifier from
configs/layerN.yaml, with environment-variable checkpoint overrides.

This is the "configuration-driven, not hard-coded" mechanism Phase 4
requires: nothing here hard-codes a path that only exists in one
environment (e.g. the Google Drive `/content/drive/...` path Phase 2
found in the notebooks' own output) -- every path comes from
configs/layerN.yaml, itself overridable per-layer via an environment
variable, without any code change.
"""

import json
from pathlib import Path
from typing import Optional

from public_pulse.models.layer1 import Layer1Classifier
from public_pulse.models.layer2 import Layer2Classifier
from public_pulse.models.layer4 import Layer4Classifier
from public_pulse.utils.config import load_config
from public_pulse.utils.paths import resolve_repo_path

_LAYER_REGISTRY = {
    "layer1": (Layer1Classifier, "configs/layer1.yaml", "PUBLIC_PULSE_LAYER1_CHECKPOINT_PATH"),
    "layer2": (Layer2Classifier, "configs/layer2.yaml", "PUBLIC_PULSE_LAYER2_CHECKPOINT_PATH"),
    "layer4": (Layer4Classifier, "configs/layer4.yaml", "PUBLIC_PULSE_LAYER4_CHECKPOINT_PATH"),
}


def _read_real_model_version(checkpoint_path: Path) -> Optional[str]:
    """Read a version string from a real, locally present
    training_metadata.json, if one exists next to the checkpoint.
    Returns None if no such file exists -- this must never be invented.
    """
    # checkpoint_path is expected at models/<layer>/checkpoints/best_model;
    # training_metadata.json (per the notebooks' own save cells) is
    # written one level up, at models/<layer>/training_metadata.json.
    metadata_path = checkpoint_path.parent.parent / "training_metadata.json"
    if not metadata_path.exists():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    base_model = metadata.get("base_model", "unknown")
    trained_at = metadata.get("trained_at") or metadata.get("random_seed")
    return f"{base_model}@{trained_at}" if trained_at is not None else str(base_model)


def build_classifier(layer_name: str):
    """Build a single layer's classifier from its config file.

    Does NOT call .load() -- construction is cheap and always succeeds;
    loading (which requires a real checkpoint + torch/transformers) is
    deferred until predict()/predict_batch() are actually called, or
    until .load() is called explicitly.
    """
    if layer_name not in _LAYER_REGISTRY:
        raise ValueError(f"Unknown layer '{layer_name}'. Expected one of {list(_LAYER_REGISTRY)}.")

    classifier_cls, config_relative_path, env_override_var = _LAYER_REGISTRY[layer_name]

    config_path = resolve_repo_path(config_relative_path)
    config = load_config(str(config_path))

    checkpoint_path = resolve_repo_path(config["checkpoint_path"], env_override_var=env_override_var)
    label_map_path = resolve_repo_path(config["label_map_path"])
    max_seq_length = config.get("max_seq_length", 256)

    model_version = _read_real_model_version(checkpoint_path)

    return classifier_cls(
        checkpoint_path=str(checkpoint_path),
        label_map_path=str(label_map_path),
        max_seq_length=max_seq_length,
        model_version=model_version,
    )


def build_all_classifiers() -> dict:
    """Build all three active layer classifiers. Convenience for the cascade."""
    return {layer_name: build_classifier(layer_name) for layer_name in _LAYER_REGISTRY}
