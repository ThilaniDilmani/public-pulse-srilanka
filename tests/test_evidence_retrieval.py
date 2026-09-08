"""Comprehensive unit and integration test suite for Phase 8 Evidence Extraction & Retrieval.

Validates empty database, no matching evidence, topic filtering, stance filtering, date filtering,
multilingual handling, noise exclusion, confidence thresholds, duplicate control, video diversity capping,
contradictory/multi-stance preservation, deterministic ranking, EvidenceSet reproducibility, persistence
idempotency, Layer 3 absence, privacy safeguards, and Top-K limit enforcement.
"""

from datetime import datetime, timezone
import pytest

from public_pulse.database.models import (
    Comment,
    Evidence,
    EvidenceSet,
    LayerEnum,
    LayerPrediction,
    ModelVersion,
    ProcessingStatusEnum,
)
from public_pulse.database.repository import (
    get_evidence_set,
    upsert_channel,
    upsert_comment,
    upsert_program,
    upsert_video,
)
from public_pulse.evidence.config import RetrievalConfig
from public_pulse.evidence.retriever import EvidenceRetriever


# ===========================================================================
# Helper Fixtures & Test Data Generators
# ===========================================================================

def _create_scored_comment(
    db,
    suffix: str,
    text_raw: str = "මේක හොඳයි සුපිරිම තමයි",
    l1_label: str = "VALID",
    l1_conf: float = 0.95,
    l2_label: str = "TOPIC_ECON_SERV",
    l2_conf: float = 0.90,
    l4_label: str = "STANCE_CRIT",
    l4_conf: float = 0.88,
    like_count: int = 10,
    posted_at: datetime = None,
    video_suffix: str = None,
):
    ch = upsert_channel(db, youtube_channel_id=f"UC_R_{suffix}", name=f"Channel_{suffix}")
    pr = upsert_program(db, channel_id=ch.id, name=f"Program_{suffix}")
    effective_video_suffix = video_suffix if video_suffix is not None else suffix
    vi = upsert_video(db, program_id=pr.id, youtube_video_id=f"VID_R_{effective_video_suffix}")

    # Ensure model versions exist
    m1 = db.query(ModelVersion).filter_by(layer=LayerEnum.layer1).first()
    if not m1:
        m1 = ModelVersion(layer=LayerEnum.layer1, checkpoint_ref="m1", is_active=True)
        db.add(m1)
    m2 = db.query(ModelVersion).filter_by(layer=LayerEnum.layer2).first()
    if not m2:
        m2 = ModelVersion(layer=LayerEnum.layer2, checkpoint_ref="m2", is_active=True)
        db.add(m2)
    m4 = db.query(ModelVersion).filter_by(layer=LayerEnum.layer4).first()
    if not m4:
        m4 = ModelVersion(layer=LayerEnum.layer4, checkpoint_ref="m4", is_active=True)
        db.add(m4)
    db.flush()

    status = ProcessingStatusEnum.scored if l1_label == "VALID" else ProcessingStatusEnum.noise_exit

    co = upsert_comment(
        db,
        video_id=vi.id,
        youtube_comment_id=f"COMM_R_{suffix}",
        text_raw=text_raw,
        text_clean=text_raw,
    )
    co.processing_status = status
    co.like_count = like_count
    if posted_at:
        co.posted_at = posted_at
    else:
        co.posted_at = datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc)

    # Predictions
    p1 = LayerPrediction(
        comment_id=co.id,
        model_version_id=m1.id,
        layer=LayerEnum.layer1,
        label=l1_label,
        label_id=0 if l1_label == "VALID" else 1,
        confidence=l1_conf,
    )
    db.add(p1)

    if l1_label == "VALID":
        p2 = LayerPrediction(
            comment_id=co.id,
            model_version_id=m2.id,
            layer=LayerEnum.layer2,
            label=l2_label,
            label_id=0,
            confidence=l2_conf,
        )
        p4 = LayerPrediction(
            comment_id=co.id,
            model_version_id=m4.id,
            layer=LayerEnum.layer4,
            label=l4_label,
            label_id=0,
            confidence=l4_conf,
        )
        db.add_all([p2, p4])

    db.commit()
    return co


# ===========================================================================
# Unit and Integration Tests
# ===========================================================================

def test_empty_database_retrieval(db):
    """Retrieval on an empty database returns an empty EvidencePayload gracefully."""
    retriever = EvidenceRetriever(RetrievalConfig(top_k=10))
    payload = retriever.retrieve(db=db)

    assert payload.evidence_count == 0
    assert payload.total_matching_count == 0
    assert payload.evidence_items == []


def test_no_matching_evidence(db):
    """Retrieval returns 0 evidence when filters match no comments."""
    _create_scored_comment(db, suffix="nomatch", l2_label="TOPIC_ECON_SERV")
    retriever = EvidenceRetriever(RetrievalConfig(topic="TOPIC_FOR", top_k=10))
    payload = retriever.retrieve(db=db)

    assert payload.evidence_count == 0
    assert payload.total_matching_count == 0


def test_topic_filtering(db):
    """Filters comments matching specified Layer 2 topic."""
    c1 = _create_scored_comment(db, suffix="t1", l2_label="TOPIC_ECON_SERV")
    _create_scored_comment(db, suffix="t2", l2_label="TOPIC_GOV")

    retriever = EvidenceRetriever(RetrievalConfig(topic="TOPIC_ECON_SERV", top_k=10))
    payload = retriever.retrieve(db=db)

    assert payload.evidence_count == 1
    assert payload.evidence_items[0].comment_id == str(c1.id)
    assert payload.evidence_items[0].layer2_topic == "TOPIC_ECON_SERV"


def test_stance_filtering(db):
    """Filters comments matching specified Layer 4 stance when explicitly requested."""
    c1 = _create_scored_comment(db, suffix="s1", l4_label="STANCE_CRIT")
    _create_scored_comment(db, suffix="s2", l4_label="STANCE_SUPP")

    retriever = EvidenceRetriever(RetrievalConfig(stance="STANCE_CRIT", top_k=10))
    payload = retriever.retrieve(db=db)

    assert payload.evidence_count == 1
    assert payload.evidence_items[0].comment_id == str(c1.id)
    assert payload.evidence_items[0].layer4_stance == "STANCE_CRIT"


def test_date_range_filtering(db):
    """Restricts comments strictly within posted_at date window."""
    d1 = datetime(2026, 1, 10, tzinfo=timezone.utc)
    d2 = datetime(2026, 2, 10, tzinfo=timezone.utc)

    c1 = _create_scored_comment(db, suffix="d1", posted_at=d1)
    _create_scored_comment(db, suffix="d2", posted_at=d2)

    cfg = RetrievalConfig(
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 20, tzinfo=timezone.utc),
        top_k=10,
    )
    payload = EvidenceRetriever(cfg).retrieve(db=db)

    assert payload.evidence_count == 1
    assert payload.evidence_items[0].comment_id == str(c1.id)


def test_multilingual_comments(db):
    """Handles Sinhala, Singlish, English, and Code-mixed comments cleanly."""
    t_sin = "මේක නියම වැඩක් ආර්ථිකය"
    t_sing = "gammata elakiri economy eka"
    t_eng = "Good economic policy proposal"

    c_sin = _create_scored_comment(db, suffix="m_sin", text_raw=t_sin)
    c_sing = _create_scored_comment(db, suffix="m_sing", text_raw=t_sing)
    c_eng = _create_scored_comment(db, suffix="m_eng", text_raw=t_eng)

    payload = EvidenceRetriever(RetrievalConfig(top_k=10)).retrieve(db=db)

    assert payload.evidence_count == 3
    retrieved_texts = {item.text_raw for item in payload.evidence_items}
    assert retrieved_texts == {t_sin, t_sing, t_eng}


def test_noise_exclusion(db):
    """Strictly excludes NOISE comments and noise_exit status."""
    c_valid = _create_scored_comment(db, suffix="n_val", l1_label="VALID")
    _create_scored_comment(db, suffix="n_noise", l1_label="NOISE")

    payload = EvidenceRetriever(RetrievalConfig(top_k=10)).retrieve(db=db)

    assert payload.evidence_count == 1
    assert payload.evidence_items[0].comment_id == str(c_valid.id)


def test_confidence_threshold_configuration(db):
    """Configurable min_layer2_confidence threshold excludes low-confidence predictions."""
    c_high = _create_scored_comment(db, suffix="conf_hi", l2_conf=0.92)
    _create_scored_comment(db, suffix="conf_lo", l2_conf=0.55)

    cfg = RetrievalConfig(min_layer2_confidence=0.80, top_k=10)
    payload = EvidenceRetriever(cfg).retrieve(db=db)

    assert payload.evidence_count == 1
    assert payload.evidence_items[0].comment_id == str(c_high.id)


def test_duplicate_text_deduplication(db):
    """Exact and near-duplicate text strings are deduplicated across comments."""
    text_dup = "නියම වැඩක් සුපිරිම තමයි මොකද කියන්නේ"
    c1 = _create_scored_comment(db, suffix="dup1", text_raw=text_dup, like_count=50)
    _create_scored_comment(db, suffix="dup2", text_raw=text_dup, like_count=5)

    payload = EvidenceRetriever(RetrievalConfig(top_k=10)).retrieve(db=db)

    assert payload.evidence_count == 1
    assert payload.evidence_items[0].comment_id == str(c1.id)  # Higher likes item retained


def test_video_diversity_cap(db):
    """Enforces max_per_video limit to prevent single video dominance."""
    _create_scored_comment(db, suffix="v1_c1", video_suffix="same_vid", text_raw="ආර්ථිකය ගැන හොඳ අදහස් ඇත", like_count=100)
    _create_scored_comment(db, suffix="v1_c2", video_suffix="same_vid", text_raw="ජනාධිපති කළ ප්‍රකාශය ගැන", like_count=90)
    _create_scored_comment(db, suffix="v1_c3", video_suffix="same_vid", text_raw="රටේ ප්‍රශ්න විසඳිය යුතු යයි", like_count=80)
    c_v2 = _create_scored_comment(db, suffix="v2_c1", video_suffix="other_vid", text_raw="වෙනත් වීඩියෝ ප්‍රතිචාරය", like_count=70)

    cfg = RetrievalConfig(max_per_video=2, top_k=10)
    payload = EvidenceRetriever(cfg).retrieve(db=db)

    assert payload.evidence_count == 3
    video_ids = [item.video_id for item in payload.evidence_items]
    assert video_ids.count(video_ids[0]) <= 2


def test_contradictory_mixed_stance_preservation(db):
    """When stance='ALL', preserves proportional representation across CRIT, NEUT, SUPP."""
    _create_scored_comment(db, suffix="st_c1", l4_label="STANCE_CRIT", text_raw="ආණ්ඩුව කරන දේ නරකයි")
    _create_scored_comment(db, suffix="st_c2", l4_label="STANCE_CRIT", text_raw="ප්‍රතිපත්ති ක්‍රමය ගැන විරෝධය")
    _create_scored_comment(db, suffix="st_n1", l4_label="STANCE_NEUT", text_raw="සාමාන්‍ය අදහස් දෙකම ඇත")
    _create_scored_comment(db, suffix="st_s1", l4_label="STANCE_SUPP", text_raw="ආර්ථිකය හොඳ දිශාවක යයි")

    cfg = RetrievalConfig(stance="ALL", top_k=4)
    payload = EvidenceRetriever(cfg).retrieve(db=db)

    assert payload.evidence_count == 4
    stances = {item.layer4_stance for item in payload.evidence_items}
    assert "STANCE_CRIT" in stances
    assert "STANCE_NEUT" in stances
    assert "STANCE_SUPP" in stances


def test_deterministic_ranking_and_tie_breaking(db):
    """Verifies same query over same database state yields 100% identical ordered evidence."""
    t_shared = "ආර්ථික ප්‍රශ්නය ගැන"
    d_fixed = datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc)
    _create_scored_comment(db, suffix="det1", text_raw=t_shared, like_count=10, posted_at=d_fixed)
    _create_scored_comment(db, suffix="det2", text_raw=t_shared + " දෙකක්", like_count=20, posted_at=d_fixed)
    _create_scored_comment(db, suffix="det3", text_raw=t_shared + " තුනක්", like_count=10, posted_at=d_fixed)

    cfg = RetrievalConfig(top_k=10, keywords=["ආර්ථික"])
    res1 = EvidenceRetriever(cfg).retrieve(db=db)
    res2 = EvidenceRetriever(cfg).retrieve(db=db)

    ids1 = [item.comment_id for item in res1.evidence_items]
    ids2 = [item.comment_id for item in res2.evidence_items]

    assert ids1 == ids2
    assert len(ids1) == 3


def test_evidence_set_reproducibility(db):
    """Verifies EvidenceSet can be re-fetched by evidence_set_id with matching provenance."""
    _create_scored_comment(db, suffix="rep1", text_raw="Reproducibility test comment data")

    cfg = RetrievalConfig(top_k=5)
    payload = EvidenceRetriever(cfg).retrieve(db=db)

    ev_set_id = payload.evidence_set_id
    db_set = get_evidence_set(db, ev_set_id)

    assert db_set is not None
    assert str(db_set.id) == ev_set_id
    assert db_set.query_params["top_k"] == 5
    assert len(db_set.evidence_items) == payload.evidence_count


def test_evidence_persistence_and_idempotency(db):
    """Verifies evidence records persist in DB without creating duplicate items on re-insertion."""
    co = _create_scored_comment(db, suffix="idem1", text_raw="Idempotency verification test comment")

    cfg = RetrievalConfig(top_k=5)
    payload1 = EvidenceRetriever(cfg).retrieve(db=db)
    payload2 = EvidenceRetriever(cfg).retrieve(db=db)

    # Historical EvidenceSets remain distinct
    assert payload1.evidence_set_id != payload2.evidence_set_id
    assert db.query(EvidenceSet).count() == 2

    # Evidence items inside each EvidenceSet match exactly
    s1 = get_evidence_set(db, payload1.evidence_set_id)
    assert len(s1.evidence_items) == 1
    assert s1.evidence_items[0].comment_id == co.id


def test_layer3_absence_guard():
    """Confirms Layer 3 is nowhere present in retrieval logic, config, or exported models."""
    cfg = RetrievalConfig()
    assert not hasattr(cfg, "layer3")
    assert "layer3" not in cfg.to_dict()
    layer_values = {e.value for e in LayerEnum}
    assert "layer3" not in layer_values


def test_privacy_anonymization_guard(db):
    """Confirms no raw user handles, author identity, or PII are exposed in evidence payloads."""
    co = _create_scored_comment(db, suffix="priv1", text_raw="Privacy test comment data")
    co.author_hash = "abc123anonymizedhash"
    db.commit()

    payload = EvidenceRetriever(RetrievalConfig(top_k=5)).retrieve(db=db)
    item = payload.evidence_items[0]

    item_dict = item.to_dict()
    assert "author_hash" not in item_dict
    assert "user_id" not in item_dict
    assert "username" not in item_dict


def test_top_k_limit_enforcement(db):
    """Verifies evidence set size strictly respects requested top_k parameter."""
    for i in range(10):
        _create_scored_comment(db, suffix=f"k_{i}", text_raw=f"Comment number {i}")

    cfg = RetrievalConfig(top_k=3)
    payload = EvidenceRetriever(cfg).retrieve(db=db)

    assert payload.evidence_count == 3
    assert len(payload.evidence_items) == 3


def test_structured_query_provenance(db):
    """Verifies query parameters are persisted as structured JSON in EvidenceSet."""
    _create_scored_comment(db, suffix="prov1", text_raw="Provenance test comment data")

    cfg = RetrievalConfig(topic="TOPIC_ECON_SERV", stance="STANCE_CRIT", top_k=5)
    payload = EvidenceRetriever(cfg).retrieve(db=db)

    db_set = get_evidence_set(db, payload.evidence_set_id)
    assert db_set.query_params["topic"] == "TOPIC_ECON_SERV"
    assert db_set.query_params["stance"] == "STANCE_CRIT"
    assert db_set.query_params["top_k"] == 5
