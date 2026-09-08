"""Tests for evidence retrieval API endpoints (Phase 11)."""

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
def setup_evidence_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    c = Channel(name="Swarnawahini", youtube_channel_id="UCcijXxFzSXgoM6q9cCtT9PA")
    db.add(c)
    db.flush()

    p = Program(channel_id=c.id, name="Rathu ira (Swarnawahini)", platform="youtube")
    db.add(p)
    db.flush()

    mv1 = ModelVersion(layer=LayerEnum.layer1, checkpoint_ref="c1", is_active=True)
    mv2 = ModelVersion(layer=LayerEnum.layer2, checkpoint_ref="c2", is_active=True)
    mv4 = ModelVersion(layer=LayerEnum.layer4, checkpoint_ref="c4", is_active=True)
    db.add_all([mv1, mv2, mv4])
    db.flush()

    v = Video(program_id=p.id, youtube_video_id="v_rathu_01", title="Rathu Ira Discussion")
    db.add(v)
    db.flush()

    cm = Comment(
        video_id=v.id,
        youtube_comment_id="c_ev_01",
        author_hash="SECRET_AUTHOR_HASH_123",
        text_raw="Raw text about economy in Colombo",
        text_clean="Clean text about economy in Colombo",
        posted_at=datetime.now(timezone.utc),
        processing_status=ProcessingStatusEnum.scored,
    )
    db.add(cm)
    db.flush()

    p1 = LayerPrediction(comment_id=cm.id, model_version_id=mv1.id, layer=LayerEnum.layer1, label="VALID", label_id=0, confidence=0.95)
    p2 = LayerPrediction(comment_id=cm.id, model_version_id=mv2.id, layer=LayerEnum.layer2, label="TOPIC_ECON_SERV", label_id=0, confidence=0.85)
    p3 = LayerPrediction(comment_id=cm.id, model_version_id=mv4.id, layer=LayerEnum.layer4, label="STANCE_CRIT", label_id=0, confidence=0.88)
    db.add_all([p1, p2, p3])

    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=engine)


def test_evidence_retrieval_success():
    req = {
        "top_k": 5,
        "stance": "ALL",
    }
    res = client.post("/api/v1/evidence/retrieve", json=req)
    assert res.status_code == 200, res.json()
    data = res.json()
    assert "evidence_set_id" in data
    assert data["evidence_count"] >= 1
    assert data["retrieval_method"] == "hybrid_bm25_v1"

    raw_str = res.text
    assert "SECRET_AUTHOR_HASH_123" not in raw_str
    assert "Raw text about economy in Colombo" not in raw_str
    assert "author_hash" not in raw_str
    assert "text_raw" not in raw_str


def test_evidence_retrieval_invalid_top_k():
    req = {"top_k": 500}
    res = client.post("/api/v1/evidence/retrieve", json=req)
    assert res.status_code == 422
