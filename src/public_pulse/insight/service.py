"""Insight Service orchestrator managing generation workflow and database persistence (Phase 9)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from public_pulse.database.models import Insight
from public_pulse.database.repository import insert_insight
from public_pulse.evidence.models import EvidencePayload
from public_pulse.insight.config import InsightGeneratorConfig
from public_pulse.insight.generator import GroundedInsightGenerator
from public_pulse.insight.models import GeneratedInsight

log = logging.getLogger(__name__)


class InsightService:
    """Orchestrates Phase 9 grounded insight generation and database persistence."""

    def __init__(
        self,
        config: Optional[InsightGeneratorConfig] = None,
        generator: Optional[GroundedInsightGenerator] = None,
    ):
        self.config = config or InsightGeneratorConfig()
        self.generator = generator or GroundedInsightGenerator(config=self.config)

    def generate_and_persist(
        self,
        db: Session,
        payload: EvidencePayload,
        dry_run: bool = False,
    ) -> GeneratedInsight:
        """Generate a grounded insight from EvidencePayload and persist to database."""
        log.info(
            "Generating insight for evidence_set_id %s (count=%d)...",
            payload.evidence_set_id,
            payload.evidence_count,
        )

        insight_obj = self.generator.generate(payload)
        insight_type = f"grounded_llm_{self.config.prompt_version}"

        if not dry_run:
            program_id = payload.retrieval_metadata.get("program_id")
            ev_set_id = payload.evidence_set_id
            if ev_set_id is not None:
                from public_pulse.database.repository import get_evidence_set
                if get_evidence_set(db, ev_set_id) is None:
                    ev_set_id = None

            db_record = insert_insight(
                db,
                evidence_set_id=ev_set_id,
                program_id=program_id,
                insight_type=insight_type,
                payload_json=insight_obj.to_dict(),
                generation_status=insight_obj.status,
                error_message=insight_obj.error_message,
                llm_provider=insight_obj.llm_provider,
                llm_model=insight_obj.llm_model,
                prompt_version=insight_obj.prompt_version,
                generation_params_json=insight_obj.generation_params,
            )
            db.commit()
            log.info("Persisted Insight record %s (status=%s)", db_record.id, db_record.generation_status)

        return insight_obj
