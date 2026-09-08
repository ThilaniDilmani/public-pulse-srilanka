"""Tests for catalog API endpoints (Phase 11)."""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.deps import engine, SessionLocal
from public_pulse.database.models import Base, Channel, Program, Video

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Seed sample channel, program, video
    c = Channel(name="Hiru News Channel", youtube_channel_id="UCckltLEhFLv8Xz_lQhYfwmg")
    db.add(c)
    db.flush()

    p = Program(channel_id=c.id, name="Hiru Salakuna (Hiru)", platform="youtube")
    db.add(p)
    db.flush()

    v = Video(program_id=p.id, youtube_video_id="vid_101", title="Salakuna Episode 101")
    db.add(v)
    db.commit()
    db.close()

    yield
    Base.metadata.drop_all(bind=engine)


def test_health_endpoint():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["phases_complete"] == 10
    assert "ABSENT" in data["subissue_status"]


def test_list_channels():
    res = client.get("/api/v1/channels")
    assert res.status_code == 200
    channels = res.json()
    assert len(channels) == 1
    assert channels[0]["name"] == "Hiru News Channel"
    assert "youtube_channel_id" not in channels[0]


def test_get_channel_by_id():
    res = client.get("/api/v1/channels")
    c_id = res.json()[0]["id"]
    res_single = client.get(f"/api/v1/channels/{c_id}")
    assert res_single.status_code == 200
    assert res_single.json()["name"] == "Hiru News Channel"


def test_list_channel_programs():
    res_c = client.get("/api/v1/channels")
    c_id = res_c.json()[0]["id"]
    res_p = client.get(f"/api/v1/channels/{c_id}/programs")
    assert res_p.status_code == 200
    programs = res_p.json()
    assert len(programs) == 1
    assert programs[0]["name"] == "Hiru Salakuna (Hiru)"
    assert programs[0]["channel_name"] == "Hiru News Channel"


def test_list_programs():
    res = client.get("/api/v1/programs")
    assert res.status_code == 200
    programs = res.json()
    assert len(programs) == 1
    assert programs[0]["name"] == "Hiru Salakuna (Hiru)"


def test_get_program_by_id():
    res_p = client.get("/api/v1/programs")
    p_id = res_p.json()[0]["id"]
    res = client.get(f"/api/v1/programs/{p_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Hiru Salakuna (Hiru)"


def test_list_program_videos():
    res_p = client.get("/api/v1/programs")
    p_id = res_p.json()[0]["id"]
    res_v = client.get(f"/api/v1/programs/{p_id}/videos")
    assert res_v.status_code == 200
    videos = res_v.json()
    assert len(videos) == 1
    assert videos[0]["title"] == "Salakuna Episode 101"
    assert "youtube_video_id" not in videos[0]


def test_channel_not_found():
    res = client.get("/api/v1/channels/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


def test_program_not_found():
    res = client.get("/api/v1/programs/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404
