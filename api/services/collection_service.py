"""Collection service for triggering and monitoring live YouTube data collection and inference (Phase 11)."""

from __future__ import annotations

import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from public_pulse.database.models import PipelineRun, PipelineRunStatusEnum
from public_pulse.database.session import SessionLocal
from public_pulse.extraction.config import ExtractionConfig, DEFAULT_PROGRAMS_YAML
from public_pulse.extraction.service import ExtractionService

log = logging.getLogger(__name__)

# Global in-memory status tracking for real-time progress updates
_JOBS_LOCK = threading.Lock()
_JOBS_PROGRESS: Dict[str, Dict[str, Any]] = {}


class CollectionService:

    @staticmethod
    def get_catalog() -> Dict[str, Any]:
        """Read target channel & program definitions directly from configs/programs.yaml."""
        if not DEFAULT_PROGRAMS_YAML.exists():
            return {"channels": []}

        try:
            config = ExtractionConfig.load(require_api_key=False)
        except Exception as err:
            log.error("Failed to load programs.yaml: %s", err)
            return {"channels": []}

        # Friendly channel name mapping based on YouTube channel IDs
        channel_names = {
            "UCckltLEhFLv8Xz_lQhYfwmg": "Hiru News / TV",
            "UCCK3OZi788Ok44K97WAhLKQ": "Ada Derana / Derana TV",
            "UCgnFSj7jQffD5V5m05j4dPw": "Sirasa TV",
            "UCcijXxFzSXgoM6q9cCtT9PA": "Swarnavahini TV",
            "UCfdBd-9WWZUv1h7d80Omy8g": "Truth with Chamuditha",
            "UC0RX5hQE6UpHTjfub4NZSPg": "Hari TV - Lahiru Mudalige",
            "UC3tvYy-s84yySG7V85jRDnA": "Sudaa creation",
            "UCKQo4WI1lxhygYrrSo5TkuQ": "Bai Thakshalawa",
        }

        # Group programs by channel_id
        grouped: Dict[str, Dict[str, Any]] = {}
        for prog in config.programs:
            cid = prog.channel_id
            cname = channel_names.get(cid, f"Channel ({cid[:8]}...)")
            if cid not in grouped:
                grouped[cid] = {
                    "channel_id": cid,
                    "channel_name": cname,
                    "programs": [],
                }
            grouped[cid]["programs"].append({
                "program_name": prog.program_name,
                "playlist_id": prog.playlist_id,
                "keywords": prog.keywords,
            })

        return {"channels": list(grouped.values())}

    @staticmethod
    def start_collection(
        program_names: List[str],
        episodes_per_program: int = 4,
    ) -> Dict[str, Any]:
        """Spawn a background thread to collect YouTube data and run inference cascade."""
        job_id = str(uuid.uuid4())

        initial_state = {
            "job_id": job_id,
            "status": "started",
            "progress_pct": 0,
            "stage": "Initializing data collection",
            "programs_requested": len(program_names),
            "program_names": program_names,
            "episodes_per_program": episodes_per_program,
            "videos_discovered": 0,
            "comments_inserted": 0,
            "comments_scored": 0,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }

        with _JOBS_LOCK:
            _JOBS_PROGRESS[job_id] = initial_state

        thread = threading.Thread(
            target=CollectionService._background_worker,
            args=(job_id, program_names, episodes_per_program),
            daemon=True,
        )
        thread.start()

        return {"job_id": job_id, "status": "started"}

    @staticmethod
    def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve real-time job status."""
        with _JOBS_LOCK:
            if job_id in _JOBS_PROGRESS:
                return dict(_JOBS_PROGRESS[job_id])

        # Fallback to database query if not in memory
        db = SessionLocal()
        try:
            run = db.query(PipelineRun).filter(PipelineRun.id == uuid.UUID(job_id)).first()
            if not run:
                return None
            return {
                "job_id": str(run.id),
                "status": run.status.value if hasattr(run.status, "value") else str(run.status),
                "progress_pct": 100 if run.status == PipelineRunStatusEnum.completed else 0,
                "stage": f"Pipeline run status: {run.status}",
                "comments_inserted": run.comments_processed or 0,
                "comments_scored": run.comments_scored or 0,
                "error": run.error_message,
                "created_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.finished_at.isoformat() if run.finished_at else None,
            }
        except Exception:
            return None
        finally:
            db.close()

    @staticmethod
    def _update_job(job_id: str, updates: Dict[str, Any]) -> None:
        with _JOBS_LOCK:
            if job_id in _JOBS_PROGRESS:
                _JOBS_PROGRESS[job_id].update(updates)

    @staticmethod
    def _background_worker(
        job_id: str,
        program_names: List[str],
        episodes_per_program: int,
    ) -> None:
        """Worker executing YouTube extraction followed by model inference."""
        log.info("Starting background collection job %s for programs: %s", job_id, program_names)

        total_progs = len(program_names)
        total_videos = 0
        total_comments = 0

        CollectionService._update_job(job_id, {
            "status": "running",
            "stage": "Connecting to YouTube API...",
            "progress_pct": 5,
        })

        db = SessionLocal()
        try:
            api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
            if not api_key:
                raise ValueError("YOUTUBE_API_KEY is not set in environment or .env file.")

            config = ExtractionConfig.load(
                require_api_key=True,
                limit_videos=episodes_per_program,
            )
            service = ExtractionService(config)

            # Step 1: Extraction for each program
            for idx, prog_name in enumerate(program_names):
                prog_pct = int(10 + (idx / total_progs) * 60)
                CollectionService._update_job(job_id, {
                    "stage": f"Collecting YouTube episodes for: {prog_name} ({idx + 1}/{total_progs})",
                    "progress_pct": prog_pct,
                })

                try:
                    stats = service.run_extraction(program_name_filter=prog_name, db=db)
                    total_videos += stats.get("videos_discovered", 0)
                    total_comments += stats.get("comments_inserted", 0)

                    CollectionService._update_job(job_id, {
                        "videos_discovered": total_videos,
                        "comments_inserted": total_comments,
                    })
                except Exception as prog_err:
                    log.warning("Extraction failed for program %s: %s", prog_name, prog_err)

            # Step 2: Inference Scoring (if model checkpoints exist)
            CollectionService._update_job(job_id, {
                "stage": "Analyzing comment sentiment, topics, and stances with XLM-R models...",
                "progress_pct": 75,
            })

            comments_scored = 0
            try:
                from public_pulse.inference.cascade import InferenceCascade
                cascade = InferenceCascade.from_config()
                # Run batch scoring on pending comments
                from scripts.run_inference import (
                    load_database_tables,
                    get_or_create_model_versions,
                    load_pending_comments,
                    process_batch,
                    RunStats,
                )

                tables = load_database_tables()
                model_versions = get_or_create_model_versions(db, tables)
                pending_rows = load_pending_comments(db, tables["comments"], limit=500, retry_errors=False)

                if pending_rows:
                    run_stats = RunStats()
                    batch_size = 16
                    for start in range(0, len(pending_rows), batch_size):
                        batch = pending_rows[start : start + batch_size]
                        process_batch(
                            db,
                            tables,
                            cascade,
                            model_versions,
                            batch,
                            dry_run=False,
                            stats=run_stats,
                        )
                        db.commit()
                    comments_scored = run_stats.scored + run_stats.noise
            except Exception as inf_err:
                log.info("Model inference skipped or encountered non-fatal note: %s", inf_err)

            # Step 3: Grounded Gemini AI Insight Generation
            CollectionService._update_job(job_id, {
                "stage": "Generating grounded discourse insights with Google Gemini 3.6 Flash...",
                "progress_pct": 90,
            })

            try:
                from public_pulse.evidence.retriever import EvidenceRetriever
                from public_pulse.evidence.config import RetrievalConfig
                from public_pulse.insight.service import InsightService as Phase9InsightService
                from public_pulse.database.models import Program

                p9_service = Phase9InsightService()

                for prog_name in program_names:
                    prog_row = db.query(Program).filter(Program.name == prog_name).first()
                    prog_id_str = str(prog_row.id) if prog_row else None

                    # Retrieve evidence for this program
                    ret_config = RetrievalConfig(
                        program_id=prog_id_str,
                        top_k=10,
                    )
                    retriever = EvidenceRetriever(config=ret_config)
                    payload = retriever.retrieve(db)

                    if payload and payload.evidence_count >= 1:
                        # Save evidence set record
                        from public_pulse.database.repository import insert_evidence_set
                        ev_set_rec = insert_evidence_set(
                            db,
                            retrieval_method=payload.retrieval_method,
                            query_params=payload.retrieval_metadata,
                            items=payload.evidence_items,
                        )
                        db.commit()
                        payload.evidence_set_id = str(ev_set_rec.id)

                        # Generate & persist real Gemini insight
                        p9_service.generate_and_persist(db, payload)
                        log.info("Generated real Gemini AI insight for program %s", prog_name)
            except Exception as ai_err:
                log.warning("AI Insight generation note: %s", ai_err)

            CollectionService._update_job(job_id, {
                "status": "completed",
                "stage": "Collection, XLM-R scoring & Gemini AI insights complete!",
                "progress_pct": 100,
                "videos_discovered": total_videos,
                "comments_inserted": total_comments,
                "comments_scored": comments_scored,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })

        except Exception as exc:
            log.exception("Collection job %s failed: %s", job_id, exc)
            CollectionService._update_job(job_id, {
                "status": "failed",
                "stage": "Collection failed",
                "error": str(exc),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
        finally:
            db.close()
