"""Tests for faithfulness verification API endpoints (Phase 11)."""

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
    ModelVersion,
    ProcessingStatusEnum,
    Program,
    Video,
)
from public_pulse.database.repository import (
    insert_evidence_set,
    insert_insight,
    insert_verification_result,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_verification_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    c = Channel(name="Sirasa TV", youtube_channel_id="UCgnFSj7jQffD5V5m05j4dPw")
    db.add(c)
    db.flush()

    p = Program(channel_id=c.id, name="Sirasa Satana", platform="youtube")
    db.add(p)
    db.flush()

    v = Video(program_id=p.id, youtube_video_id="v_satana_01", title="Satana Episode 01")
    db.add(v)
    db.flush()

    cm = Comment(
        video_id=v.id,
        youtube_comment_id="c_vf_01",
        text_raw="Raw comment for verification",
        text_clean="Clean comment for verification",
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
        "summary": "Verified insight summary.",
        "findings": [
            {
                "finding_id": "F1",
                "text": "Clean comment for verification.",
                "evidence_ids": [str(es.evidence_items[0].id)],
                "confidence": "high",
            }
        ],
        "discourse_interpretation": "Interp.",
        "limitations": "None.",
        "uncertainty_note": "None.",
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

    vdetails = {
        "claim_support_rate": 1.0,
        "partial_support_rate": 0.0,
        "unsupported_claim_rate": 0.0,
        "contradiction_rate": 0.0,
        "grounding_score": 1.0,
        "evidence_citation_precision": 1.0,
        "total_claims_evaluated": 1,
        "claim_verifications": [
            {
                "claim_id": "F1-C1",
                "finding_id": "F1",
                "claim_text": "Clean comment for verification.",
                "label": "SUPPORTED",
                "evidence_ids": [str(es.evidence_items[0].id)],
                "verification_method": "deterministic_heuristic",
                "reason": "Exact match found in evidence.",
            }
        ],
    }

    insert_verification_result(
        db,
        insight_id=ins.id,
        evidence_set_id=es.id,
        verifier_method="hybrid_nli_v1",
        verifier_model="deterministic_heuristic",
        grounding_score=1.0,
        claim_support_rate=1.0,
        unsupported_claim_rate=0.0,
        contradiction_rate=0.0,
        verification_details_json=vdetails,
    )

    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=engine)


def test_get_verification_report():
    db = SessionLocal()
    ins = db.query(Insight).first()
    ins_id = str(ins.id)
    db.close()

    res = client.get(f"/api/v1/insights/{ins_id}/verification")
    assert res.status_code == 200
    data = res.json()
    assert data["insight_id"] == ins_id
    assert data["grounding_score"] == 1.0
    assert data["claim_support_rate"] == 1.0
    assert len(data["claim_verifications"]) == 1
    assert data["claim_verifications"][0]["label"] == "SUPPORTED"


def test_trigger_verification_202():
    db = SessionLocal()
    ins = db.query(Insight).first()
    ins_id = str(ins.id)
    db.close()

    res = client.post(f"/api/v1/insights/{ins_id}/verify")
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "completed"


def test_verification_404():
    res = client.get("/api/v1/insights/00000000-0000-0000-0000-000000000000/verification")
    assert res.status_code == 404
