"""Tests for insight generation and retrieval API endpoints (Phase 11)."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from api.main import app
from api.deps import engine, SessionLocal
from public_pulse.database.models import (
    Base,
    Channel,
    Comment,
    EvidenceSet,
    Insight,
    LayerEnum,
    LayerPrediction,
    ModelVersion,
    ProcessingStatusEnum,
    Program,
    Video,
)
from public_pulse.database.repository import insert_evidence_set, insert_insight

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_insights_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    c = Channel(name="Derana", youtube_channel_id="UCCK3OZi788Ok44K97WAhLKQ")
    db.add(c)
    db.flush()

    p = Program(channel_id=c.id, name="Wada pitiyaa (Ada derana)", platform="youtube")
    db.add(p)
    db.flush()

    v = Video(program_id=p.id, youtube_video_id="v_wada_01", title="Wada Pitiya Show")
    db.add(v)
    db.flush()

    cm = Comment(
        video_id=v.id,
        youtube_comment_id="c_ins_01",
        text_raw="Raw comment",
        text_clean="Clean comment",
        posted_at=datetime.now(timezone.utc),
        processing_status=ProcessingStatusEnum.scored,
    )
    db.add(cm)
    db.flush()

    es = insert_evidence_set(
        db,
        query_params={"top_k": 5},
        retrieval_method="hybrid_bm25_v1",
        items=[
            {
                "comment_id": cm.id,
                "evidence_type": "bm25",
                "layer": "layer2",
                "label": "TOPIC_ECON_SERV",
                "confidence": 0.9,
                "relevance_score": 0.85,
                "rank": 1,
            }
        ],
    )

    ins_payload = {
        "summary": "Public expresses concern regarding cost of living.",
        "findings": [
            {
                "finding_id": "F1",
                "text": "Inflation remains a primary topic of criticism.",
                "evidence_ids": [str(es.evidence_items[0].id)],
                "confidence": "high",
            }
        ],
        "discourse_interpretation": "Critique dominates discourse.",
        "limitations": "Sample size is limited.",
        "uncertainty_note": "Uncertainty low.",
        "evidence_count_used": 1,
        "stance_distribution": {"STANCE_CRIT": 1.0},
    }

    ins = insert_insight(
        db,
        evidence_set_id=es.id,
        program_id=p.id,
        insight_type="grounded_llm_v1",
        payload_json=ins_payload,
        generation_status="completed",
        llm_provider="mock",
        llm_model="mock-model",
        prompt_version="v1",
    )

    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=engine)


def test_get_insight_by_id():
    db = SessionLocal()
    ins = db.query(Insight).first()
    ins_id = str(ins.id)
    db.close()

    res = client.get(f"/api/v1/insights/{ins_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["insight_id"] == ins_id
    assert data["generation_status"] == "completed"
    assert "cost of living" in data["summary"]
    assert len(data["findings"]) == 1
    assert data["findings"][0]["finding_id"] == "F1"


def test_list_insights():
    res = client.get("/api/v1/insights")
    assert res.status_code == 200
    insights = res.json()
    assert len(insights) >= 1


def test_trigger_insight_generation_202():
    db = SessionLocal()
    es = db.query(EvidenceSet).first()
    es_id = str(es.id)
    db.close()

    req = {"evidence_set_id": es_id}
    res = client.post("/api/v1/insights/generate", json=req)
    assert res.status_code == 202
    data = res.json()
    assert "job_id" in data
    assert data["job_type"] == "insight_generation"


def test_get_insight_404():
    res = client.get("/api/v1/insights/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
