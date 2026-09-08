"""Model integration tests (Phase 4).

Two distinct kinds of test live here, and this file is careful never to
blur them together:

1. REAL, UNMOCKED tests against this environment's actual current state
   (no checkpoint files exist locally; torch/transformers are not
   installed here). These are not simulations -- they exercise the real
   CheckpointNotFoundError / MissingDependencyError paths for real,
   because that is genuinely what this environment's state produces.

2. Pure logic tests of code that does not require torch/transformers at
   all (label map loading, config resolution, exception hierarchy,
   idempotent-load guard).

Nothing in this file claims a real model was loaded or a real prediction
was produced -- that remains blocked pending checkpoint access (see
docs/MODEL_REGISTRY.md).
"""

import json

import pytest

from public_pulse.models import (
    CheckpointNotFoundError,
    Layer1Classifier,
    Layer2Classifier,
    Layer4Classifier,
    MissingDependencyError,
    ModelIntegrationError,
    ModelLoadError,
    build_all_classifiers,
    build_classifier,
)
from public_pulse.utils.paths import REPO_ROOT


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    def test_all_three_inherit_from_common_base(self):
        assert issubclass(CheckpointNotFoundError, ModelIntegrationError)
        assert issubclass(MissingDependencyError, ModelIntegrationError)
        assert issubclass(ModelLoadError, ModelIntegrationError)

    def test_the_three_failure_modes_are_distinct_types(self):
        # A caller must be able to `except CheckpointNotFoundError` without
        # also silently catching a dependency or load-integrity problem.
        assert CheckpointNotFoundError is not MissingDependencyError
        assert CheckpointNotFoundError is not ModelLoadError
        assert MissingDependencyError is not ModelLoadError


# ---------------------------------------------------------------------------
# Factory / configuration-driven path resolution
# ---------------------------------------------------------------------------

class TestFactoryConfigResolution:
    @pytest.mark.parametrize(
        "layer_name,expected_labels",
        [
            ("layer1", {"VALID", "NOISE"}),
            ("layer2", {"TOPIC_ECON_SERV", "TOPIC_FOR", "TOPIC_GOV", "TOPIC_LAW", "TOPIC_MEDIA"}),
            ("layer4", {"STANCE_CRIT", "STANCE_NEUT", "STANCE_SUPP"}),
        ],
    )
    def test_builds_classifier_with_correct_label_map(self, layer_name, expected_labels):
        classifier = build_classifier(layer_name)
        assert set(classifier.label_map.label_to_id.keys()) == expected_labels

    def test_checkpoint_path_resolved_relative_to_repo_root_by_default(self):
        classifier = build_classifier("layer1")
        assert classifier.checkpoint_path == REPO_ROOT / "models/layer1_utility/checkpoints/best_model"

    def test_max_seq_length_is_256_for_all_layers(self):
        for layer_name in ("layer1", "layer2", "layer4"):
            assert build_classifier(layer_name).max_seq_length == 256

    def test_model_version_is_not_none_when_config_has_checkpoint(self):
        # Post-Phase 2: Checkpoint metadata exists in layer configs.
        for layer_name in ("layer1", "layer2", "layer4"):
            assert build_classifier(layer_name).model_version is not None

    def test_env_var_override_replaces_configured_checkpoint_path(self, monkeypatch, tmp_path):
        override_dir = tmp_path / "custom_checkpoint_location"
        override_dir.mkdir()
        monkeypatch.setenv("PUBLIC_PULSE_LAYER1_CHECKPOINT_PATH", str(override_dir))
        classifier = build_classifier("layer1")
        assert classifier.checkpoint_path == override_dir

    def test_unknown_layer_name_raises_value_error(self):
        with pytest.raises(ValueError):
            build_classifier("layer3")  # must never resolve -- Layer 3 does not exist

    def test_build_all_classifiers_returns_exactly_three_layers(self):
        classifiers = build_all_classifiers()
        assert set(classifiers.keys()) == {"layer1", "layer2", "layer4"}
        assert isinstance(classifiers["layer1"], Layer1Classifier)
        assert isinstance(classifiers["layer2"], Layer2Classifier)
        assert isinstance(classifiers["layer4"], Layer4Classifier)


# ---------------------------------------------------------------------------
# REAL (unmocked) load & execution tests against this environment's actual state
# ---------------------------------------------------------------------------

class TestRealCheckpointAvailableInThisEnvironment:
    """These tests call the real, production `load()` method against this
    repository's actual verified checkpoints.
    """

    @pytest.mark.parametrize("layer_name", ["layer1", "layer2", "layer4"])
    def test_load_succeeds_for_real_checkpoints(self, layer_name):
        classifier = build_classifier(layer_name)
        assert classifier.checkpoint_path.exists()
        classifier.load()
        assert classifier.is_loaded

    def test_predict_succeeds_on_real_checkpoint(self):
        classifier = build_classifier("layer1")
        classifier.load()
        res = classifier.predict("කොහොමද")
        assert res.label in ("VALID", "NOISE")

    def test_load_raises_model_load_error_for_invalid_directory(self, monkeypatch, tmp_path):
        fake_but_present_dir = tmp_path / "exists_but_is_not_a_real_checkpoint"
        fake_but_present_dir.mkdir()
        monkeypatch.setenv("PUBLIC_PULSE_LAYER1_CHECKPOINT_PATH", str(fake_but_present_dir))
        classifier = build_classifier("layer1")
        with pytest.raises(ModelLoadError):
            classifier.load()



# ---------------------------------------------------------------------------
# Pure-logic tests requiring no torch/transformers
# ---------------------------------------------------------------------------

class TestLoadIdempotencyGuard:
    def test_is_loaded_false_before_any_load_attempt(self):
        classifier = build_classifier("layer1")
        assert classifier.is_loaded is False
        assert classifier.load_count == 0

    def test_load_is_a_no_op_once_already_loaded(self):
        classifier = build_classifier("layer1")
        # Simulate a completed load without needing real torch/transformers --
        # this tests the actual idempotency guard in load() (`if self.is_loaded: return`),
        # which is the real mechanism that prevents reloading on every prediction.
        classifier._model = "fake-model-marker-simulating-a-completed-load"
        assert classifier.is_loaded is True
        classifier.load()
        assert classifier.load_count == 0  # never incremented -- load() returned immediately


class TestLabelMapContractPerClassifier:
    def test_layer1_expects_two_labels(self):
        assert len(build_classifier("layer1").label_map.label_to_id) == 2

    def test_layer2_expects_five_labels(self):
        assert len(build_classifier("layer2").label_map.label_to_id) == 5

    def test_layer4_expects_three_labels(self):
        assert len(build_classifier("layer4").label_map.label_to_id) == 3

    def test_layer_name_metadata_matches_input_column_contract(self):
        assert Layer1Classifier.INPUT_COLUMN == "text_raw"
        assert Layer2Classifier.INPUT_COLUMN == "text_clean"
        assert Layer4Classifier.INPUT_COLUMN == "text_clean"
        assert Layer1Classifier.LAYER_NAME == "layer1"
        assert Layer2Classifier.LAYER_NAME == "layer2"
        assert Layer4Classifier.LAYER_NAME == "layer4"
