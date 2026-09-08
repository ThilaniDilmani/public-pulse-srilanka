"""Privacy, security, and architectural integrity tests for Phase 11 API."""

import os
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
def setup_privacy_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    c = Channel(name="Hiru News", youtube_channel_id="UCckltLEhFLv8Xz_lQhYfwmg")
    db.add(c)
    db.flush()

    p = Program(channel_id=c.id, name="Hiru Balaya (Hiru)", platform="youtube")
    db.add(p)
    db.flush()

    v = Video(program_id=p.id, youtube_video_id="v_sec_01", title="Balaya Episode")
    db.add(v)
    db.flush()

    cm = Comment(
        video_id=v.id,
        youtube_comment_id="c_sec_01",
        author_hash="CLASSIFIED_AUTHOR_HASH_99999",
        text_raw="Raw text containing PII phone 0771234567",
        text_clean="Clean text without PII",
        posted_at=datetime.now(timezone.utc),
        processing_status=ProcessingStatusEnum.scored,
    )
    db.add(cm)
    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=engine)


def test_no_author_hash_or_text_raw_in_channels_api():
    res = client.get("/api/v1/channels")
    text = res.text
    assert "CLASSIFIED_AUTHOR_HASH" not in text
    assert "author_hash" not in text
    assert "text_raw" not in text


def test_no_author_hash_or_text_raw_in_programs_api():
    res = client.get("/api/v1/programs")
    text = res.text
    assert "CLASSIFIED_AUTHOR_HASH" not in text
    assert "author_hash" not in text
    assert "text_raw" not in text


def test_no_author_hash_or_text_raw_in_analytics_api():
    res = client.get("/api/v1/analytics/overview")
    text = res.text
    assert "CLASSIFIED_AUTHOR_HASH" not in text
    assert "author_hash" not in text
    assert "text_raw" not in text


def test_no_author_hash_or_text_raw_in_comments_summary():
    res = client.get("/api/v1/comments/summary")
    text = res.text
    assert "CLASSIFIED_AUTHOR_HASH" not in text
    assert "author_hash" not in text
    assert "text_raw" not in text


def test_evidence_retrieval_privacy_guarantee():
    req = {"top_k": 5}
    res = client.post("/api/v1/evidence/retrieve", json=req)
    text = res.text
    assert "CLASSIFIED_AUTHOR_HASH" not in text
    assert "author_hash" not in text
    assert "text_raw" not in text


def test_api_key_header_security(monkeypatch):
    monkeypatch.setenv("API_KEY", "supersecretkey123")

    from api.deps import verify_api_key
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(x_api_key=None)
    assert exc_info.value.status_code == 401

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(x_api_key="wrong_key")
    assert exc_info.value.status_code == 401

    assert verify_api_key(x_api_key="supersecretkey123") == "supersecretkey123"


def test_layer3_absence_in_api_package():
    import pkgutil
    import api

    for _, module_name, _ in pkgutil.walk_packages(api.__path__, api.__name__ + "."):
        mod = __import__(module_name, fromlist=["*"])
        for attr in dir(mod):
            assert "layer3" not in attr.lower()
            assert "subissue" not in attr.lower()
