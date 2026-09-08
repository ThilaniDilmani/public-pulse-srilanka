"""Tests for analytical endpoints (Phase 11)."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from api.main import app
from api.deps import engine, SessionLocal
from public_pulse.database.models import (
    Base,
    Channel,
    Comment,
    LayerEnum,
    LayerPrediction,
    ModelVersion,
    ProcessingStatusEnum,
    Program,
    Video,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_analytics_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    c = Channel(name="Derana TV", youtube_channel_id="UCCK3OZi788Ok44K97WAhLKQ")
    db.add(c)
    db.flush()

    p = Program(channel_id=c.id, name="Derana 360 (Derana)", platform="youtube")
    db.add(p)
    db.flush()

    mv1 = ModelVersion(layer=LayerEnum.layer1, checkpoint_ref="ckpt_l1", is_active=True)
    mv2 = ModelVersion(layer=LayerEnum.layer2, checkpoint_ref="ckpt_l2", is_active=True)
    mv4 = ModelVersion(layer=LayerEnum.layer4, checkpoint_ref="ckpt_l4", is_active=True)
    db.add_all([mv1, mv2, mv4])
    db.flush()

    v = Video(program_id=p.id, youtube_video_id="der_360_01", title="Derana 360 Show")
    db.add(v)
    db.flush()

    cm1 = Comment(
        video_id=v.id,
        youtube_comment_id="c1",
        text_raw="Raw text 1",
        text_clean="Clean text 1",
        posted_at=datetime.now(timezone.utc),
        processing_status=ProcessingStatusEnum.scored,
    )
    cm2 = Comment(
        video_id=v.id,
        youtube_comment_id="c2",
        text_raw="Raw text 2",
        text_clean="Clean text 2",
        posted_at=datetime.now(timezone.utc),
        processing_status=ProcessingStatusEnum.scored,
    )
    cm_noise = Comment(
        video_id=v.id,
        youtube_comment_id="c3",
        text_raw="Noise text",
        text_clean="Noise text",
        posted_at=datetime.now(timezone.utc),
        processing_status=ProcessingStatusEnum.noise_exit,
    )
    db.add_all([cm1, cm2, cm_noise])
    db.flush()

    p1 = LayerPrediction(comment_id=cm1.id, model_version_id=mv2.id, layer=LayerEnum.layer2, label="TOPIC_ECON_SERV", label_id=0, confidence=0.9)
    p2 = LayerPrediction(comment_id=cm1.id, model_version_id=mv4.id, layer=LayerEnum.layer4, label="STANCE_CRIT", label_id=0, confidence=0.85)
    p3 = LayerPrediction(comment_id=cm2.id, model_version_id=mv2.id, layer=LayerEnum.layer2, label="TOPIC_GOV", label_id=1, confidence=0.88)
    p4 = LayerPrediction(comment_id=cm2.id, model_version_id=mv4.id, layer=LayerEnum.layer4, label="STANCE_SUPP", label_id=2, confidence=0.92)
    db.add_all([p1, p2, p3, p4])

    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=engine)


def test_analytics_overview():
    res = client.get("/api/v1/analytics/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["total_comments"] == 3
    assert data["valid_comments"] == 2
    assert data["noise_comments"] == 1
    assert data["total_videos"] == 1
    assert data["total_programs"] == 1
    assert data["total_channels"] == 1


def test_topic_distribution():
    res = client.get("/api/v1/analytics/topics")
    assert res.status_code == 200
    data = res.json()
    assert data["total_valid_comments"] == 2
    dist = {d["topic"]: d["count"] for d in data["distribution"]}
    assert dist["TOPIC_ECON_SERV"] == 1
    assert dist["TOPIC_GOV"] == 1


def test_stance_distribution():
    res = client.get("/api/v1/analytics/stances")
    assert res.status_code == 200
    data = res.json()
    assert data["total_valid_comments"] == 2
    dist = {d["stance"]: d["count"] for d in data["distribution"]}
    assert dist["STANCE_CRIT"] == 1
    assert dist["STANCE_SUPP"] == 1


def test_topic_stance_matrix():
    res = client.get("/api/v1/analytics/topic-stance-matrix")
    assert res.status_code == 200
    matrix = res.json()["matrix"]
    assert matrix["TOPIC_ECON_SERV"]["STANCE_CRIT"] == 1
    assert matrix["TOPIC_GOV"]["STANCE_SUPP"] == 1


def test_entity_matrix_program_topic():
    res = client.get("/api/v1/analytics/entity-matrix?entity_type=program&matrix_type=topic")
    assert res.status_code == 200
    data = res.json()
    assert data["entity_type"] == "program"
    assert data["matrix_type"] == "topic"
    assert "Derana 360 (Derana)" in data["matrix"]


def test_volume_over_time():
    res = client.get("/api/v1/analytics/volume-over-time?granularity=daily")
    assert res.status_code == 200
    data = res.json()
    assert len(data["data_points"]) >= 1


def test_period_over_period():
    res = client.get("/api/v1/analytics/period-over-period?period_days=30")
    assert res.status_code == 200
    data = res.json()
    assert "current_period" in data
    assert "previous_period" in data


def test_episode_analytics():
    res = client.get("/api/v1/analytics/episodes")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Derana 360 Show"


def test_data_quality_analytics():
    res = client.get("/api/v1/analytics/data-quality")
    assert res.status_code == 200
    data = res.json()
    assert "overview" in data
    assert "average_confidence_by_layer" in data
    assert "ABSENT" in data["subissue_status"]


def test_sentiment_backwards_compat():
    res = client.get("/api/v1/sentiment")
    assert res.status_code == 200
    assert "distribution" in res.json()


def test_topics_backwards_compat():
    res = client.get("/api/v1/topics")
    assert res.status_code == 200
    assert "distribution" in res.json()
