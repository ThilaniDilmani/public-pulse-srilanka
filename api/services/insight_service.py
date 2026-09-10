"""Insight API service connecting REST endpoints to Phase 9 Grounded Insight Generator (Phase 11).

Insight generation runs asynchronously via background worker.
"""

from typing import List, Optional
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from public_pulse.database import repository
from public_pulse.evidence.models import EvidenceItem, EvidencePayload
from public_pulse.insight.service import InsightService as Phase9InsightService
from api.schemas.insight import FindingOut, InsightGenerationIn, InsightOut, JobStatusOut
from api.services.job_service import JobService
from api.deps import SessionLocal


def _bg_generate_insight(job_id: str, evidence_set_id: str, program_id: Optional[str]):
    """Background task function for generating insight."""
    db = SessionLocal()
    try:
        JobService.update_job(db, job_id, status="running")

        es = repository.get_evidence_set(db, evidence_set_id)
        if not es:
            JobService.update_job(db, job_id, status="error", error="EvidenceSet not found")
            return

        # Reconstruct EvidencePayload from EvidenceSet
        items = []
        for rank, ev in enumerate(es.evidence_items, 1):
            comment = ev.comment
            video = comment.video if comment else None
            program = video.program if video else None
            channel = program.channel if program else None

            # Retrieve layer predictions
            l2_label = ev.label or "TOPIC_ECON_SERV"
            l2_conf = ev.confidence or 0.8
            l4_label = "STANCE_CRIT"
            l4_conf = 0.8

            if comment and comment.predictions:
                for pred in comment.predictions:
                    if pred.layer == "layer2":
                        l2_label = pred.label
                        l2_conf = pred.confidence
                    elif pred.layer == "layer4":
                        l4_label = pred.label
                        l4_conf = pred.confidence

            items.append(
                EvidenceItem(
                    rank=ev.rank or rank,
                    evidence_id=str(ev.id),
                    comment_id=str(ev.comment_id),
                    text_raw=comment.text_raw if comment else "",
                    text_clean=comment.text_clean if comment else "",
                    posted_at=comment.posted_at.isoformat() if comment and comment.posted_at else "",
                    video_id=str(comment.video_id) if comment else "",
                    video_title=video.title if video else "",
                    program_name=program.name if program else "",
                    channel_name=channel.name if channel else "",
                    layer2_topic=l2_label,
                    layer2_confidence=l2_conf,
                    layer4_stance=l4_label,
                    layer4_confidence=l4_conf,
                    like_count=comment.like_count if comment else 0,
                    relevance_score=ev.relevance_score or 0.8,
                )
            )

        payload = EvidencePayload(
            evidence_set_id=str(es.id),
            retrieved_at=es.retrieved_at.isoformat(),
            retrieval_metadata=es.query_params or {},
            evidence_count=len(items),
            total_matching_count=len(items),
            retrieval_method=es.retrieval_method,
            evidence_items=items,
        )

        p9_service = Phase9InsightService()
        generated = p9_service.generate_and_persist(db, payload)

        # Retrieve inserted insight record ID
        inserted_insight = (
            db.query(repository.Insight)
            .filter(repository.Insight.evidence_set_id == es.id)
            .order_by(repository.desc(repository.Insight.generated_at))
            .first()
        )
        insight_id = str(inserted_insight.id) if inserted_insight else None

        JobService.update_job(db, job_id, status="completed", reference_id=insight_id)
    except Exception as e:
        JobService.update_job(db, job_id, status="error", error=str(e))
    finally:
        db.close()


class InsightApiService:

    @staticmethod
    def trigger_generation(
        db: Session,
        background_tasks: BackgroundTasks,
        request: InsightGenerationIn,
    ) -> JobStatusOut:
        es = repository.get_evidence_set(db, request.evidence_set_id)
        if not es:
            raise ValueError(f"EvidenceSet {request.evidence_set_id} not found")

        job = JobService.create_job(db, job_type="insight_generation", reference_id=request.evidence_set_id)
        background_tasks.add_task(
            _bg_generate_insight, job.job_id, request.evidence_set_id, request.program_id
        )
        return job

    @staticmethod
    def get_insight(db: Session, insight_id: str) -> Optional[InsightOut]:
        ins = repository.get_insight(db, insight_id)
        if not ins:
            return None

        payload = ins.payload_json or {}
        findings_data = payload.get("findings", [])
        findings = [
            FindingOut(
                finding_id=f.get("finding_id", ""),
                text=f.get("text", ""),
                evidence_ids=f.get("evidence_ids", []),
                confidence=f.get("confidence", "high"),
            )
            for f in findings_data
        ]

        return InsightOut(
            insight_id=str(ins.id),
            evidence_set_id=str(ins.evidence_set_id) if ins.evidence_set_id else None,
            program_id=str(ins.program_id) if ins.program_id else None,
            insight_type=ins.insight_type,
            generation_status=ins.generation_status,
            summary=payload.get("summary"),
            findings=findings,
            discourse_interpretation=payload.get("discourse_interpretation"),
            limitations=payload.get("limitations"),
            uncertainty_note=payload.get("uncertainty_note"),
            llm_provider=ins.llm_provider or "mock",
            llm_model=ins.llm_model or "mock-model",
            prompt_version=ins.prompt_version or "v1",
            generated_at=ins.generated_at.isoformat(),
            evidence_count_used=payload.get("evidence_count_used", 0),
            stance_distribution=payload.get("stance_distribution"),
            error_message=ins.error_message,
        )

    @staticmethod
    def list_insights(
        db: Session,
        program_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        generation_status: Optional[str] = None,
    ) -> List[InsightOut]:
        insights = repository.list_insights(
            db, program_id=program_id, limit=limit, offset=offset, generation_status=generation_status
        )
        res = []
        for ins in insights:
            i_out = InsightApiService.get_insight(db, str(ins.id))
            if i_out:
                res.append(i_out)
        return res
