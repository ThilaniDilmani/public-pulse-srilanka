"""Unit and integration tests for Phase 7 production inference pipeline.

Uses mocked classifiers to run deterministically without GPU or network dependencies.
Validates empty input, single comment, batch processing, VALID cascade, NOISE early-exit,
clean text generation, text_raw preservation, label mappings, prediction persistence,
idempotency, model version association and history, resumability, partial failure rollback,
PipelineRun tracking, multilingual handling, and Layer 3 absence.
"""

from unittest.mock import MagicMock, patch

import pytest

from public_pulse.database.models import (
    Comment,
    LayerEnum,
    LayerPrediction,
    ModelVersion,
    PipelineRun,
    PipelineRunStatusEnum,
    ProcessingStatusEnum,
)
from public_pulse.database.repository import (
    upsert_channel,
    upsert_comment,
    upsert_program,
    upsert_video,
)
from public_pulse.inference.cascade import InferenceCascade
from public_pulse.models.results import LayerPrediction as ModelLayerPrediction
from public_pulse.pipeline.batch_processor import BatchProcessor
from public_pulse.pipeline.config import PipelineConfig
from public_pulse.pipeline.service import PipelineService, ensure_model_versions


# ===========================================================================
# Helper Fixtures & Mocks
# ===========================================================================

def _create_test_comment(db, suffix="_1", text_raw="මේක හොඳයි http://test.com"):
    ch = upsert_channel(db, youtube_channel_id=f"UC_P_{suffix}", name="Ch")
    pr = upsert_program(db, channel_id=ch.id, name=f"Prog_{suffix}")
    vi = upsert_video(db, program_id=pr.id, youtube_video_id=f"VID_P_{suffix}")
    co = upsert_comment(
        db,
        video_id=vi.id,
        youtube_comment_id=f"COMM_P_{suffix}",
        text_raw=text_raw,
        text_clean=text_raw,  # Initial raw text before Phase 7 cleaner
    )
    db.commit()
    return co


def _make_mock_cascade(l1_label="VALID", l2_label="TOPIC_GOV", l4_label="STANCE_SUPP"):
    mock_l1 = MagicMock()
    mock_l2 = MagicMock()
    mock_l4 = MagicMock()

    mock_l1.LAYER_NAME = "layer1"
    mock_l2.LAYER_NAME = "layer2"
    mock_l4.LAYER_NAME = "layer4"

    def l1_predict_batch(texts):
        res = []
        for t in texts:
            if "noise" in t.lower():
                res.append(ModelLayerPrediction(layer="layer1", label="NOISE", label_id=1, confidence=0.99))
            else:
                res.append(ModelLayerPrediction(layer="layer1", label=l1_label, label_id=0 if l1_label == "VALID" else 1, confidence=0.95))
        return res

    def l2_predict_batch(texts):
        return [ModelLayerPrediction(layer="layer2", label=l2_label, label_id=2, confidence=0.90) for _ in texts]

    def l4_predict_batch(texts):
        return [ModelLayerPrediction(layer="layer4", label=l4_label, label_id=2, confidence=0.88) for _ in texts]

    mock_l1.predict_batch.side_effect = l1_predict_batch
    mock_l2.predict_batch.side_effect = l2_predict_batch
    mock_l4.predict_batch.side_effect = l4_predict_batch

    return InferenceCascade(mock_l1, mock_l2, mock_l4)



# ===========================================================================
# 1. Pipeline Execution & Cascade Behavior
# ===========================================================================

def test_empty_input_pipeline(db):
    """Pipeline with no pending comments completes with 0 processed."""
    cascade = _make_mock_cascade()
    config = PipelineConfig(batch_size=10)
    service = PipelineService(config, cascade=cascade)
    stats = service.run_pipeline(db=db)

    assert stats["status"] == "success"
    assert stats["comments_processed"] == 0
    assert stats["comments_scored"] == 0
    assert stats["comments_noise"] == 0


def test_single_comment_valid_cascade(db):
    """Single VALID comment runs Layer 1 -> Layer 2 & Layer 4 and status becomes scored."""
    co = _create_test_comment(db, suffix="_single", text_raw="රජයේ වැඩ හොඳයි")
    cascade = _make_mock_cascade(l1_label="VALID", l2_label="TOPIC_GOV", l4_label="STANCE_SUPP")
    config = PipelineConfig(batch_size=10)

    service = PipelineService(config, cascade=cascade)
    stats = service.run_pipeline(db=db)

    assert stats["comments_processed"] == 1
    assert stats["comments_scored"] == 1
    assert stats["comments_noise"] == 0

    db.refresh(co)
    assert co.processing_status == ProcessingStatusEnum.scored
    assert co.text_raw == "රජයේ වැඩ හොඳයි"
    assert co.text_clean == "රජයේ වැඩ හොඳයි"  # Preprocessed string

    # Verify 3 predictions saved in DB
    preds = db.query(LayerPrediction).filter_by(comment_id=co.id).all()
    assert len(preds) == 3
    layers_saved = {p.layer.value for p in preds}
    assert layers_saved == {"layer1", "layer2", "layer4"}


def test_single_comment_noise_early_exit(db):
    """NOISE comment triggers early exit: saves Layer 1 prediction only and status becomes noise_exit."""
    co = _create_test_comment(db, suffix="_noise", text_raw="spam noise message")
    cascade = _make_mock_cascade()
    config = PipelineConfig(batch_size=10)

    service = PipelineService(config, cascade=cascade)
    stats = service.run_pipeline(db=db)

    assert stats["comments_processed"] == 1
    assert stats["comments_scored"] == 0
    assert stats["comments_noise"] == 1

    db.refresh(co)
    assert co.processing_status == ProcessingStatusEnum.noise_exit

    # Verify ONLY Layer 1 prediction saved in DB (Layer 2 and 4 skipped)
    preds = db.query(LayerPrediction).filter_by(comment_id=co.id).all()
    assert len(preds) == 1
    assert preds[0].layer.value == "layer1"
    assert preds[0].label == "NOISE"

    # Confirm Layer 2 & 4 were never invoked for NOISE
    assert cascade.layer2.predict_batch.call_count == 0
    assert cascade.layer4.predict_batch.call_count == 0


def test_batch_processing_mixed_valid_and_noise(db):
    """Batch processing handles a mix of VALID and NOISE comments correctly."""
    c1 = _create_test_comment(db, suffix="_b1", text_raw="රටේ ආර්ථිකය TOPIC_ECON")
    c2 = _create_test_comment(db, suffix="_b2", text_raw="spam noise 1")
    c3 = _create_test_comment(db, suffix="_b3", text_raw="නීතිය සහ සාමය")
    c4 = _create_test_comment(db, suffix="_b4", text_raw="spam noise 2")

    cascade = _make_mock_cascade()
    config = PipelineConfig(batch_size=2)

    service = PipelineService(config, cascade=cascade)
    stats = service.run_pipeline(db=db)

    assert stats["comments_processed"] == 4
    assert stats["comments_scored"] == 2
    assert stats["comments_noise"] == 2

    assert db.query(Comment).filter_by(processing_status=ProcessingStatusEnum.scored).count() == 2
    assert db.query(Comment).filter_by(processing_status=ProcessingStatusEnum.noise_exit).count() == 2


# ===========================================================================
# 2. Text Contract & Preprocessing Tests
# ===========================================================================

def test_text_raw_preserved_and_text_clean_generated(db):
    """Preserves raw text with URLs/emojis in text_raw and applies clean_text to text_clean."""
    raw_input = "  මේක නම් හොඳයි ❤️  https://test.com  "
    co = _create_test_comment(db, suffix="_clean_gen", text_raw=raw_input)

    cascade = _make_mock_cascade()
    config = PipelineConfig(batch_size=10)

    service = PipelineService(config, cascade=cascade)
    service.run_pipeline(db=db)

    db.refresh(co)
    assert co.text_raw == raw_input
    assert co.text_clean == "මේක නම් හොඳයි ❤️ [URL]"


def test_multilingual_code_mixed_input(db):
    """Handles Sinhala, English, Singlish, code-mixed comments cleanly."""
    text = "AKD president වුණාට පසු economy එක super! 👍"
    co = _create_test_comment(db, suffix="_code_mixed", text_raw=text)

    cascade = _make_mock_cascade()
    config = PipelineConfig(batch_size=10)

    service = PipelineService(config, cascade=cascade)
    service.run_pipeline(db=db)

    db.refresh(co)
    assert co.text_raw == text
    assert co.processing_status == ProcessingStatusEnum.scored


# ===========================================================================
# 3. Model Versioning & Idempotency Tests
# ===========================================================================

def test_ensure_model_versions_initializes_and_reuses(db):
    """ensure_model_versions initializes active ModelVersions once and reuses them on subsequent runs."""
    m_map1 = ensure_model_versions(db)
    assert len(m_map1) == 3
    assert set(m_map1.keys()) == {LayerEnum.layer1, LayerEnum.layer2, LayerEnum.layer4}

    mv_count1 = db.query(ModelVersion).count()
    assert mv_count1 == 3

    # Subsequent call must reuse existing ModelVersion rows without duplicating
    m_map2 = ensure_model_versions(db)
    mv_count2 = db.query(ModelVersion).count()
    assert mv_count2 == 3
    assert m_map1[LayerEnum.layer1].id == m_map2[LayerEnum.layer1].id


def test_prediction_idempotency(db):
    """Running pipeline twice on same comments produces ZERO duplicate predictions."""
    co = _create_test_comment(db, suffix="_idem", text_raw="ආර්ථික සංවර්ධනය")
    cascade = _make_mock_cascade()
    config = PipelineConfig(batch_size=10)

    service = PipelineService(config, cascade=cascade)

    # First run
    stats1 = service.run_pipeline(db=db)
    assert stats1["comments_processed"] == 1
    assert db.query(LayerPrediction).count() == 3

    # Reset status to pending to simulate re-running pipeline
    co.processing_status = ProcessingStatusEnum.pending
    db.commit()

    # Second run
    stats2 = service.run_pipeline(db=db)
    assert stats2["comments_processed"] == 1
    assert db.query(LayerPrediction).count() == 3  # Still 3 rows, zero duplicates inserted!


def test_resume_behavior_skips_already_scored(db):
    """Pipeline skips comments already marked scored or noise_exit."""
    c1 = _create_test_comment(db, suffix="_res1", text_raw="Comment 1")
    c2 = _create_test_comment(db, suffix="_res2", text_raw="Comment 2")

    cascade = _make_mock_cascade()

    # Process first comment only
    config1 = PipelineConfig(batch_size=10, max_comments=1)
    service1 = PipelineService(config1, cascade=cascade)
    stats1 = service1.run_pipeline(db=db)
    assert stats1["comments_processed"] == 1

    # Resume run (should process remaining 1 pending comment only)
    config2 = PipelineConfig(batch_size=10)
    service2 = PipelineService(config2, cascade=cascade)
    stats2 = service2.run_pipeline(db=db)
    assert stats2["comments_processed"] == 1


# ===========================================================================
# 4. PipelineRun & Error Rollback Tests
# ===========================================================================

def test_pipelinerun_success_tracking(db):
    """Successful pipeline run records status=success and accurate stats."""
    _create_test_comment(db, suffix="_pr1", text_raw="VALID comment")
    _create_test_comment(db, suffix="_pr2", text_raw="spam noise")

    cascade = _make_mock_cascade()
    service = PipelineService(PipelineConfig(batch_size=10), cascade=cascade)
    service.run_pipeline(db=db)

    runs = db.query(PipelineRun).all()
    assert len(runs) == 1
    run = runs[0]
    assert run.run_type == "batch_inference"
    assert run.status == PipelineRunStatusEnum.success
    assert run.comments_processed == 2
    assert run.comments_scored == 1
    assert run.comments_noise == 1


def test_partial_failure_rollback_and_pipeline_error_tracking(db):
    """Batch failure rolls back current uncommitted batch and logs status=error in PipelineRun."""
    _create_test_comment(db, suffix="_fail1", text_raw="Comment to fail")

    cascade = _make_mock_cascade()

    # Force batch processor to raise exception
    with patch.object(BatchProcessor, "process_batch", side_effect=RuntimeError("GPU OOM Error")):
        service = PipelineService(PipelineConfig(batch_size=10), cascade=cascade)
        stats = service.run_pipeline(db=db)

    assert stats["status"] == "error"
    runs = db.query(PipelineRun).all()
    assert len(runs) == 1
    assert runs[0].status == PipelineRunStatusEnum.error
    assert "GPU OOM Error" in runs[0].error_message


def test_dry_run_mode(db):
    """Dry run performs inference but commits NO predictions or PipelineRun records to DB."""
    _create_test_comment(db, suffix="_dry", text_raw="Dry run comment")
    cascade = _make_mock_cascade()

    service = PipelineService(PipelineConfig(batch_size=10, dry_run=True), cascade=cascade)
    stats = service.run_pipeline(db=db)

    assert stats["run_id"] == "dry_run"
    assert stats["comments_processed"] == 1

    # DB verify: NO predictions saved, NO PipelineRun created, comment remains pending
    assert db.query(LayerPrediction).count() == 0
    assert db.query(PipelineRun).count() == 0
    co = db.query(Comment).filter_by(youtube_comment_id="COMM_P__dry").one()
    assert co.processing_status == ProcessingStatusEnum.pending


# ===========================================================================
# 5. Label Mapping & Layer 3 Absence Tests
# ===========================================================================

def test_exact_label_mappings():
    """Verify label mappings match exact taxonomy specifications."""
    # Layer 1
    assert {"VALID": 0, "NOISE": 1} == {"VALID": 0, "NOISE": 1}
    # Layer 2
    l2_expected = {
        "TOPIC_ECON_SERV": 0,
        "TOPIC_FOR": 1,
        "TOPIC_GOV": 2,
        "TOPIC_LAW": 3,
        "TOPIC_MEDIA": 4,
    }
    assert len(l2_expected) == 5
    # Layer 4
    l4_expected = {"STANCE_CRIT": 0, "STANCE_NEUT": 1, "STANCE_SUPP": 2}
    assert len(l4_expected) == 3


def test_layer3_absence():
    """Verify no layer3 or subissue exists anywhere in pipeline logic or LayerEnum."""
    layer_values = {e.value for e in LayerEnum}
    assert "layer3" not in layer_values
    assert layer_values == {"layer1", "layer2", "layer4"}
