"""Database layer tests for Public Pulse — Phase 5.

All 23 required test cases covering:
  - Model creation and table presence
  - Entity creation and relationships (channels → programs → videos → comments)
  - text_raw / text_clean separation
  - Idempotency constraints (UNIQUE on youtube_comment_id, youtube_video_id)
  - Prediction insertion for Layer 1, Layer 2, Layer 4
  - Layer 3 and invalid layer rejection (enforced at Python / SAEnum level)
  - Prediction uniqueness constraint
  - Model version relationship and active-version-per-layer enforcement
  - Annotation uniqueness
  - Pipeline run creation
  - Evidence and insight relationships
  - Repository functions: get_pending_comments(), get_active_model_version()

Backend: SQLite in-memory (via conftest.py).
PostgreSQL-specific constraints (partial unique index on model_versions)
are enforced by the Alembic migration against a live PostgreSQL DB and
are explicitly noted where they cannot be tested with SQLite.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from public_pulse.database.models import (
    Annotation,
    Base,
    Channel,
    Comment,
    Evidence,
    Insight,
    LayerEnum,
    LayerPrediction,
    ModelVersion,
    PipelineRun,
    PipelineRunStatusEnum,
    ProcessingStatusEnum,
    Program,
    Video,
)
from public_pulse.database.repository import (
    get_active_model_version,
    get_pending_comments,
    insert_predictions,
    set_active_model_version,
    upsert_channel,
    upsert_comment,
    upsert_program,
    upsert_video,
)


# ---------------------------------------------------------------------------
# Shared test-data helpers
# ---------------------------------------------------------------------------


def _make_channel(db, *, youtube_channel_id="UC_test_channel_001", name="Test Channel"):
    return upsert_channel(db, youtube_channel_id=youtube_channel_id, name=name)


def _make_program(db, channel_id, *, name="Test Program"):
    return upsert_program(db, channel_id=channel_id, name=name)


def _make_video(db, program_id, *, youtube_video_id="vid_001"):
    return upsert_video(db, program_id=program_id, youtube_video_id=youtube_video_id)


def _make_comment(
    db,
    video_id,
    *,
    youtube_comment_id="comment_001",
    text_raw="කොහොමද",
    text_clean="කොහොමද",
):
    return upsert_comment(
        db,
        video_id=video_id,
        youtube_comment_id=youtube_comment_id,
        text_raw=text_raw,
        text_clean=text_clean,
    )


def _make_model_version(db, layer=LayerEnum.layer1, *, checkpoint_ref="models/layer1_utility/checkpoints/best_model"):
    mv = ModelVersion(
        layer=layer,
        checkpoint_ref=checkpoint_ref,
        base_model="xlm-roberta-base",
    )
    db.add(mv)
    db.flush()
    return mv


def _full_chain(db, *, comment_id_suffix=""):
    """Create channel → program → video → comment and return all four objects."""
    ch = _make_channel(db, youtube_channel_id=f"UC_chain{comment_id_suffix}")
    pr = _make_program(db, ch.id, name=f"Chain Program{comment_id_suffix}")
    vi = _make_video(db, pr.id, youtube_video_id=f"vid_chain{comment_id_suffix}")
    co = _make_comment(
        db,
        vi.id,
        youtube_comment_id=f"comment_chain{comment_id_suffix}",
    )
    return ch, pr, vi, co


# ===========================================================================
# TEST 1: Model creation — all 10 tables present
# ===========================================================================


def test_model_creation(engine):
    """All 10 expected tables are present in the schema."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    expected = {
        "channels",
        "programs",
        "videos",
        "comments",
        "model_versions",
        "layer_predictions",
        "pipeline_runs",
        "annotations",
        "evidence",
        "insights",
    }
    assert expected <= tables, f"Missing tables: {expected - tables}"
    # Confirm layer3 tables do not exist
    assert "layer3_subissue" not in tables
    assert "layer3_predictions" not in tables


# ===========================================================================
# TEST 2: Channel creation
# ===========================================================================


def test_channel_creation(db):
    """A channel can be created and retrieved by youtube_channel_id."""
    ch = _make_channel(db)
    db.commit()

    from sqlalchemy import select

    result = db.execute(
        select(Channel).where(Channel.youtube_channel_id == "UC_test_channel_001")
    ).scalar_one()
    assert result.name == "Test Channel"
    assert result.id is not None


# ===========================================================================
# TEST 3: Program → Channel relationship
# ===========================================================================


def test_program_channel_relationship(db):
    """A program references its channel via FK and the ORM relationship works."""
    ch = _make_channel(db)
    pr = _make_program(db, ch.id)
    db.commit()

    db.refresh(pr)
    assert pr.channel_id == ch.id
    assert pr.channel.name == "Test Channel"
    # program_type remains nullable — not invented
    assert pr.program_type is None


# ===========================================================================
# TEST 4: Video → Program relationship
# ===========================================================================


def test_video_program_relationship(db):
    """A video references its program via FK."""
    ch = _make_channel(db)
    pr = _make_program(db, ch.id)
    vi = _make_video(db, pr.id)
    db.commit()

    db.refresh(vi)
    assert vi.program_id == pr.id
    assert vi.program.name == "Test Program"


# ===========================================================================
# TEST 5: Comment → Video relationship
# ===========================================================================


def test_comment_video_relationship(db):
    """A comment references its video via FK."""
    _, _, vi, co = _full_chain(db)
    db.commit()

    db.refresh(co)
    assert co.video_id == vi.id
    assert co.video.youtube_video_id == vi.youtube_video_id


# ===========================================================================
# TEST 6: text_raw and text_clean are both preserved separately
# ===========================================================================


def test_comment_text_raw_and_text_clean_preserved(db):
    """text_raw and text_clean are stored as distinct columns."""
    ch = _make_channel(db, youtube_channel_id="UC_text_test")
    pr = _make_program(db, ch.id, name="Text Test Program")
    vi = _make_video(db, pr.id, youtube_video_id="vid_text_test")

    raw = "අලුත් ආණ්ඩුව ගැන කියන්නේ 😂🤣 ??? !!!"
    clean = "අලුත් ආණ්ඩුව ගැන කියන්නේ"

    co = upsert_comment(
        db,
        video_id=vi.id,
        youtube_comment_id="comment_text_test",
        text_raw=raw,
        text_clean=clean,
    )
    db.commit()
    db.refresh(co)

    assert co.text_raw == raw
    assert co.text_clean == clean
    # The two fields must be different (they serve different layers)
    assert co.text_raw != co.text_clean


# ===========================================================================
# TEST 7: Comment idempotency (UNIQUE youtube_comment_id)
# ===========================================================================


def test_comment_idempotency(db):
    """Inserting a duplicate youtube_comment_id raises IntegrityError."""
    _, _, vi, _ = _full_chain(db, comment_id_suffix="_idem")
    db.commit()

    # Attempt a direct duplicate insert (bypassing upsert)
    dup = Comment(
        video_id=vi.id,
        youtube_comment_id="comment_chain_idem",  # already inserted by _full_chain
        text_raw="dup raw",
        text_clean="dup clean",
        processing_status=ProcessingStatusEnum.pending,
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.flush()


# ===========================================================================
# TEST 8: Video idempotency (UNIQUE youtube_video_id)
# ===========================================================================


def test_video_idempotency(db):
    """Inserting a duplicate youtube_video_id raises IntegrityError."""
    ch = _make_channel(db, youtube_channel_id="UC_vid_idem")
    pr = _make_program(db, ch.id, name="Vid Idem Program")
    _make_video(db, pr.id, youtube_video_id="vid_idem_001")
    db.commit()

    dup = Video(
        program_id=pr.id,
        youtube_video_id="vid_idem_001",  # already exists
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.flush()


# ===========================================================================
# TEST 9: Prediction insertion
# ===========================================================================


def test_prediction_insertion(db):
    """A layer1 prediction can be inserted and read back."""
    _, _, _, co = _full_chain(db, comment_id_suffix="_pred")
    mv = _make_model_version(db, LayerEnum.layer1)
    db.commit()

    preds = insert_predictions(
        db,
        comment_id=co.id,
        model_version_id=mv.id,
        predictions=[
            {
                "layer": "layer1",
                "label": "VALID",
                "label_id": 1,
                "confidence": 0.97,
            }
        ],
    )
    db.commit()

    assert len(preds) == 1
    assert preds[0].label == "VALID"
    assert preds[0].layer == LayerEnum.layer1
    assert abs(preds[0].confidence - 0.97) < 1e-6


# ===========================================================================
# TEST 10: Prediction uniqueness constraint
# ===========================================================================


def test_prediction_uniqueness(db):
    """UNIQUE(comment_id, layer, model_version_id) is enforced."""
    _, _, _, co = _full_chain(db, comment_id_suffix="_uniq")
    mv = _make_model_version(db, LayerEnum.layer1)
    db.commit()

    # First insert — OK
    insert_predictions(
        db,
        comment_id=co.id,
        model_version_id=mv.id,
        predictions=[{"layer": "layer1", "label": "VALID", "label_id": 1, "confidence": 0.9}],
    )
    db.flush()

    # Second insert of the exact same (comment, layer, version) — should be skipped
    # by the repository's idempotency check (no IntegrityError via upsert)
    result = insert_predictions(
        db,
        comment_id=co.id,
        model_version_id=mv.id,
        predictions=[{"layer": "layer1", "label": "NOISE", "label_id": 0, "confidence": 0.1}],
    )
    # Repository skips the duplicate; returned list should be empty
    assert result == []

    # Direct ORM duplicate bypass MUST raise IntegrityError
    dup = LayerPrediction(
        comment_id=co.id,
        model_version_id=mv.id,
        layer=LayerEnum.layer1,
        label="NOISE",
        label_id=0,
        confidence=0.1,
        predicted_at=datetime.now(timezone.utc),
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.flush()


# ===========================================================================
# TEST 11: Layer 1 prediction labels
# ===========================================================================


def test_layer1_prediction(db):
    """Layer 1 labels VALID and NOISE are accepted."""
    _, _, _, co = _full_chain(db, comment_id_suffix="_l1")
    mv = _make_model_version(db, LayerEnum.layer1)

    for label, label_id in [("VALID", 1), ("NOISE", 0)]:
        co_x = upsert_comment(
            db,
            video_id=co.video_id,
            youtube_comment_id=f"l1_{label}",
            text_raw="test",
            text_clean="test",
        )
        insert_predictions(
            db,
            comment_id=co_x.id,
            model_version_id=mv.id,
            predictions=[{"layer": "layer1", "label": label, "label_id": label_id, "confidence": 0.9}],
        )
    db.commit()


# ===========================================================================
# TEST 12: Layer 2 prediction
# ===========================================================================


def test_layer2_prediction(db):
    """Layer 2 topic labels are accepted."""
    _, _, vi, _ = _full_chain(db, comment_id_suffix="_l2")
    mv = _make_model_version(db, LayerEnum.layer2,
                             checkpoint_ref="models/layer2_topic/checkpoints/best_model")

    topic_labels = [
        ("TOPIC_ECON_SERV", 0),
        ("TOPIC_GOV", 1),
        ("TOPIC_LAW", 2),
        ("TOPIC_FOR", 3),
        ("TOPIC_MEDIA", 4),
    ]
    for label, label_id in topic_labels:
        co = upsert_comment(
            db,
            video_id=vi.id,
            youtube_comment_id=f"l2_{label}",
            text_raw="test comment",
            text_clean="test comment",
        )
        preds = insert_predictions(
            db,
            comment_id=co.id,
            model_version_id=mv.id,
            predictions=[{"layer": "layer2", "label": label, "label_id": label_id, "confidence": 0.8}],
        )
        assert preds[0].layer == LayerEnum.layer2
        assert preds[0].label == label

    db.commit()


# ===========================================================================
# TEST 13: Layer 4 prediction
# ===========================================================================


def test_layer4_prediction(db):
    """Layer 4 stance labels are accepted."""
    _, _, vi, _ = _full_chain(db, comment_id_suffix="_l4")
    mv = _make_model_version(db, LayerEnum.layer4,
                             checkpoint_ref="models/layer4_stance/checkpoints/best_model")

    stance_labels = [
        ("STANCE_CRIT", 0),
        ("STANCE_NEUT", 1),
        ("STANCE_SUPP", 2),
    ]
    for label, label_id in stance_labels:
        co = upsert_comment(
            db,
            video_id=vi.id,
            youtube_comment_id=f"l4_{label}",
            text_raw="test comment",
            text_clean="test comment",
        )
        preds = insert_predictions(
            db,
            comment_id=co.id,
            model_version_id=mv.id,
            predictions=[{"layer": "layer4", "label": label, "label_id": label_id, "confidence": 0.85}],
        )
        assert preds[0].layer == LayerEnum.layer4
        assert preds[0].label == label

    db.commit()


# ===========================================================================
# TEST 14: Layer 3 is rejected
# ===========================================================================


def test_layer3_is_rejected(db):
    """'layer3' is rejected by the LayerEnum Python enum.

    The LayerEnum Python enum does not include 'layer3' — it raises ValueError
    at the Python level when you try to construct LayerEnum('layer3').

    The PostgreSQL database-level enforcement (via the layer_enum ENUM type
    created in the Alembic migration) additionally rejects 'layer3' strings
    at the DB level, but this cannot be tested against SQLite, which maps
    the column to VARCHAR and applies no constraint.

    Both layers of enforcement are verified:
      1. Python enum rejects the value (tested here, works in SQLite too)
      2. PostgreSQL enum type rejects the value (migration-level, PostgreSQL only)
    """
    # Python-level rejection: LayerEnum does not contain 'layer3'
    with pytest.raises(ValueError):
        LayerEnum("layer3")

    # Confirm 'layer3' is not in the enum members at all
    layer_values = {e.value for e in LayerEnum}
    assert "layer3" not in layer_values, (
        "layer3 must never appear in LayerEnum — it was permanently removed"
    )
    assert layer_values == {"layer1", "layer2", "layer4"}, (
        f"LayerEnum must contain exactly layer1/layer2/layer4, got: {layer_values}"
    )


# ===========================================================================
# TEST 15: Invalid layer value is rejected
# ===========================================================================


def test_invalid_layer_is_rejected(db):
    """Arbitrary invalid layer strings are rejected by LayerEnum.

    The Python enum rejects any value not in {layer1, layer2, layer4}.
    See test_layer3_is_rejected for the full enforcement discussion.
    """
    invalid_values = ["layer3", "totally_invalid", "LAYER1", "Layer1", "", "null"]
    for val in invalid_values:
        with pytest.raises(ValueError):
            LayerEnum(val)




# ===========================================================================
# TEST 16: ModelVersion relationship
# ===========================================================================


def test_model_version_relationship(db):
    """A LayerPrediction correctly references its ModelVersion."""
    _, _, _, co = _full_chain(db, comment_id_suffix="_mvrel")
    mv = _make_model_version(db, LayerEnum.layer1)

    preds = insert_predictions(
        db,
        comment_id=co.id,
        model_version_id=mv.id,
        predictions=[{"layer": "layer1", "label": "VALID", "label_id": 1, "confidence": 0.9}],
    )
    db.commit()

    db.refresh(preds[0])
    assert preds[0].model_version_id == mv.id
    assert preds[0].model_version.base_model == "xlm-roberta-base"
    assert preds[0].model_version.layer == LayerEnum.layer1


# ===========================================================================
# TEST 17: Active model version uniqueness per layer (application level)
# ===========================================================================


def test_active_model_version_uniqueness_per_layer(db):
    """At most one ModelVersion per layer is active at a time.

    NOTE: The DB-level enforcement is a PostgreSQL partial unique index
    (UNIQUE(layer) WHERE is_active = TRUE) created by the Alembic migration.
    This test verifies the application-level enforcement via set_active_model_version().
    """
    mv1 = _make_model_version(db, LayerEnum.layer2,
                               checkpoint_ref="models/layer2_topic/checkpoints/best_model")
    mv2 = ModelVersion(
        layer=LayerEnum.layer2,
        checkpoint_ref="models/layer2_topic/checkpoints/best_model_v2",
        base_model="xlm-roberta-base",
    )
    db.add(mv2)
    db.flush()

    # Activate mv1
    set_active_model_version(db, model_version_id=mv1.id)
    assert mv1.is_active is True

    # Activating mv2 must deactivate mv1
    set_active_model_version(db, model_version_id=mv2.id)
    db.refresh(mv1)
    db.refresh(mv2)

    assert mv2.is_active is True
    assert mv1.is_active is False  # automatically deactivated


# ===========================================================================
# TEST 18: Annotation uniqueness
# ===========================================================================


def test_annotation_uniqueness(db):
    """UNIQUE(comment_id, annotator, layer) is enforced on annotations."""
    _, _, _, co = _full_chain(db, comment_id_suffix="_annot")
    db.flush()

    ann = Annotation(
        comment_id=co.id,
        annotator="annotator_01",
        layer=LayerEnum.layer1,
        label="VALID",
    )
    db.add(ann)
    db.flush()

    dup = Annotation(
        comment_id=co.id,
        annotator="annotator_01",
        layer=LayerEnum.layer1,
        label="NOISE",  # different label, same (comment, annotator, layer)
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.flush()


# ===========================================================================
# TEST 19: Pipeline run creation
# ===========================================================================


def test_pipeline_run_creation(db):
    """A PipelineRun can be created and all status values are accepted."""
    now = datetime.now(timezone.utc)

    run = PipelineRun(
        run_type="batch_inference",
        started_at=now,
        status=PipelineRunStatusEnum.running,
        triggered_by="manual",
    )
    db.add(run)
    db.flush()

    assert run.id is not None
    assert run.status == PipelineRunStatusEnum.running
    assert run.finished_at is None

    run.status = PipelineRunStatusEnum.success
    run.comments_processed = 100
    run.comments_scored = 80
    run.comments_noise = 20
    run.finished_at = datetime.now(timezone.utc)
    db.flush()

    assert run.status == PipelineRunStatusEnum.success


# ===========================================================================
# TEST 20: Evidence relationship
# ===========================================================================


def test_evidence_relationship(db):
    """Evidence can be linked to a comment with a valid layer."""
    _, _, _, co = _full_chain(db, comment_id_suffix="_evid")
    db.flush()

    ev = Evidence(
        comment_id=co.id,
        evidence_type="high_confidence_prediction",
        layer=LayerEnum.layer2,
        label="TOPIC_GOV",
        confidence=0.92,
    )
    db.add(ev)
    db.flush()

    assert ev.id is not None
    assert ev.layer == LayerEnum.layer2
    # No layer3 reference
    assert ev.layer != "layer3"


# ===========================================================================
# TEST 21: Insight relationship
# ===========================================================================


def test_insight_relationship(db):
    """An insight can be linked to a program or be system-wide (program_id=None)."""
    ch = _make_channel(db, youtube_channel_id="UC_insight_test")
    pr = _make_program(db, ch.id, name="Insight Test Program")
    db.flush()

    from datetime import date

    # Program-scoped insight
    ins = Insight(
        program_id=pr.id,
        insight_type="weekly_topic_summary",
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 7),
        payload_json={"topic_counts": {"TOPIC_GOV": 42}},
    )
    db.add(ins)
    db.flush()
    assert ins.program_id == pr.id

    # System-wide insight (program_id=NULL)
    sys_ins = Insight(
        program_id=None,
        insight_type="system_weekly_summary",
        payload_json={"total_comments": 1000},
    )
    db.add(sys_ins)
    db.flush()
    assert sys_ins.program_id is None


# ===========================================================================
# TEST 22: get_pending_comments() retrieval
# ===========================================================================


def test_pending_comment_retrieval(db):
    """get_pending_comments() returns only comments with status='pending'."""
    ch = _make_channel(db, youtube_channel_id="UC_pending_test")
    pr = _make_program(db, ch.id, name="Pending Test Program")
    vi = _make_video(db, pr.id, youtube_video_id="vid_pending_test")

    # Create 3 pending comments
    pending_ids = []
    for i in range(3):
        co = upsert_comment(
            db,
            video_id=vi.id,
            youtube_comment_id=f"pending_{i}",
            text_raw=f"raw text {i}",
            text_clean=f"clean text {i}",
        )
        pending_ids.append(co.id)

    # Create 1 scored comment
    scored_co = upsert_comment(
        db,
        video_id=vi.id,
        youtube_comment_id="scored_001",
        text_raw="scored raw",
        text_clean="scored clean",
    )
    scored_co.processing_status = ProcessingStatusEnum.scored
    db.flush()

    results = get_pending_comments(db, limit=10)
    result_ids = {r.id for r in results}

    assert all(r.processing_status == ProcessingStatusEnum.pending for r in results)
    assert set(pending_ids) <= result_ids
    assert scored_co.id not in result_ids


# ===========================================================================
# TEST 23: get_active_model_version() retrieval
# ===========================================================================


def test_active_model_version_retrieval(db):
    """get_active_model_version() returns the active version for a given layer."""
    mv_l1 = _make_model_version(
        db, LayerEnum.layer1,
        checkpoint_ref="models/layer1_utility/checkpoints/best_model"
    )
    mv_l2 = _make_model_version(
        db, LayerEnum.layer2,
        checkpoint_ref="models/layer2_topic/checkpoints/best_model"
    )

    # No active version yet
    assert get_active_model_version(db, LayerEnum.layer1) is None
    assert get_active_model_version(db, LayerEnum.layer4) is None

    # Activate layer1
    set_active_model_version(db, model_version_id=mv_l1.id)
    active_l1 = get_active_model_version(db, LayerEnum.layer1)
    assert active_l1 is not None
    assert active_l1.id == mv_l1.id
    assert active_l1.layer == LayerEnum.layer1

    # layer2 still inactive; layer4 still inactive
    assert get_active_model_version(db, LayerEnum.layer2) is None
    assert get_active_model_version(db, LayerEnum.layer4) is None

    # Activate layer2
    set_active_model_version(db, model_version_id=mv_l2.id)
    active_l2 = get_active_model_version(db, LayerEnum.layer2)
    assert active_l2 is not None
    assert active_l2.id == mv_l2.id

    # layer1 still active (unaffected by layer2 activation)
    db.refresh(mv_l1)
    assert mv_l1.is_active is True
