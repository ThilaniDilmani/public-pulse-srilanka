"""Pipeline service orchestrator and CLI entrypoint for Public Pulse (Phase 7).

Loads models once per process, manages active ModelVersion records in DB,
processes pending comments in configurable batches, updates PipelineRun stats,
and provides CLI options (--batch-size, --max-comments, --dry-run, --force-reprocess).
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from public_pulse.database.models import (
    Comment,
    LayerEnum,
    ModelVersion,
    PipelineRun,
    PipelineRunStatusEnum,
    ProcessingStatusEnum,
)
from public_pulse.database.repository import (
    get_active_model_version,
    get_pending_comments,
    set_active_model_version,
)
from public_pulse.database.session import SessionLocal
from public_pulse.inference.cascade import InferenceCascade
from public_pulse.pipeline.batch_processor import BatchProcessor
from public_pulse.pipeline.config import PipelineConfig

log = logging.getLogger(__name__)

# Default checkpoint references for model version initialization
DEFAULT_CHECKPOINT_REFS = {
    LayerEnum.layer1: "models/layer1_utility/checkpoints/best_model",
    LayerEnum.layer2: "models/layer2_topic/checkpoints/best_model",
    LayerEnum.layer4: "models/layer4_stance/checkpoints/best_model",
}


def ensure_model_versions(db: Session) -> Dict[LayerEnum, ModelVersion]:
    """Retrieve active ModelVersion for each layer, initializing if absent in DB.

    Guarantees that duplicate ModelVersion records are not created on subsequent runs.
    """
    model_version_map: Dict[LayerEnum, ModelVersion] = {}

    for layer in (LayerEnum.layer1, LayerEnum.layer2, LayerEnum.layer4):
        active_mv = get_active_model_version(db, layer)
        if active_mv is not None:
            model_version_map[layer] = active_mv
            continue

        # Check if an inactive ModelVersion exists for this checkpoint_ref
        ref = DEFAULT_CHECKPOINT_REFS[layer]
        stmt = select(ModelVersion).where(
            ModelVersion.layer == layer,
            ModelVersion.checkpoint_ref == ref,
        )
        existing_mv = db.execute(stmt).scalar_one_or_none()

        if existing_mv is not None:
            active_mv = set_active_model_version(db, model_version_id=existing_mv.id)
        else:
            new_mv = ModelVersion(
                layer=layer,
                checkpoint_ref=ref,
                base_model="xlm-roberta-base",
                is_active=True,
            )
            db.add(new_mv)
            db.flush()
            active_mv = set_active_model_version(db, model_version_id=new_mv.id)

        db.commit()
        model_version_map[layer] = active_mv
        log.info("Initialized and activated ModelVersion for %s: %s", layer.value, active_mv.id)

    return model_version_map


class PipelineService:
    """Orchestrates production inference pipeline runs across database comments."""

    def __init__(
        self,
        config: PipelineConfig,
        cascade: Optional[InferenceCascade] = None,
    ):
        self.config = config
        self.cascade = cascade  # If None, deferred to run_pipeline via from_config()

    def run_pipeline(
        self,
        db: Optional[Session] = None,
        cascade: Optional[InferenceCascade] = None,
    ) -> Dict[str, Any]:
        """Execute the production inference pipeline."""
        own_db = False
        if db is None:
            db = SessionLocal()
            own_db = True

        pipeline_run = PipelineRun(
            run_type="batch_inference",
            started_at=datetime.now(timezone.utc),
            status=PipelineRunStatusEnum.running,
            triggered_by="pipeline_service",
            comments_processed=0,
            comments_scored=0,
            comments_noise=0,
        )
        if not self.config.dry_run:
            db.add(pipeline_run)
            db.flush()

        stats = {
            "run_id": str(pipeline_run.id) if pipeline_run.id else "dry_run",
            "comments_processed": 0,
            "comments_scored": 0,
            "comments_noise": 0,
            "batches_executed": 0,
            "errors": [],
            "status": "success",
        }

        try:
            # 1. Ensure ModelVersions exist and are active
            model_version_map = ensure_model_versions(db)

            # 2. Build or use provided InferenceCascade (models loaded once per process)
            inference_cascade = cascade or self.cascade
            if inference_cascade is None:
                log.info("Loading model classifiers via InferenceCascade.from_config()...")
                inference_cascade = InferenceCascade.from_config()

            processor = BatchProcessor(
                cascade=inference_cascade,
                model_version_map=model_version_map,
                dry_run=self.config.dry_run,
            )

            # Option to force reprocess all comments
            if self.config.force_reprocess and not self.config.dry_run:
                log.info("Force reprocess specified: resetting comments processing_status to 'pending'...")
                stmt = select(Comment)
                for comment in db.execute(stmt).scalars():
                    comment.processing_status = ProcessingStatusEnum.pending
                db.commit()

            processed_comment_ids = set()
            total_processed = 0

            # 3. Batch processing loop
            while True:
                remaining_limit = self.config.batch_size
                if self.config.max_comments:
                    to_fetch = self.config.max_comments - total_processed
                    if to_fetch <= 0:
                        break
                    remaining_limit = min(remaining_limit, to_fetch)

                pending_batch = get_pending_comments(db, limit=remaining_limit)
                if processed_comment_ids:
                    pending_batch = [c for c in pending_batch if c.id not in processed_comment_ids]
                if not pending_batch:
                    log.info("No more pending comments to process.")
                    break

                log.info("Processing batch of %d pending comments...", len(pending_batch))
                b_stats = processor.process_batch(db, pending_batch)

                for c in pending_batch:
                    processed_comment_ids.add(c.id)

                stats["comments_processed"] += b_stats["processed"]
                stats["comments_scored"] += b_stats["valid"]
                stats["comments_noise"] += b_stats["noise"]
                stats["batches_executed"] += 1
                total_processed += b_stats["processed"]

            if not self.config.dry_run:
                pipeline_run.status = PipelineRunStatusEnum.success
                pipeline_run.finished_at = datetime.now(timezone.utc)
                pipeline_run.comments_processed = stats["comments_processed"]
                pipeline_run.comments_scored = stats["comments_scored"]
                pipeline_run.comments_noise = stats["comments_noise"]
                db.commit()

        except Exception as exc:
            log.exception("Pipeline execution failed: %s", exc)
            stats["status"] = "error"
            stats["errors"].append(str(exc))
            if not self.config.dry_run:
                pipeline_run.status = PipelineRunStatusEnum.error
                pipeline_run.finished_at = datetime.now(timezone.utc)
                pipeline_run.error_message = str(exc)
                db.commit()

        finally:
            if own_db:
                db.close()

        log.info(
            "Pipeline completed. Total: %d, Scored (VALID): %d, Early Exit (NOISE): %d",
            stats["comments_processed"],
            stats["comments_scored"],
            stats["comments_noise"],
        )

        return stats


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Public Pulse Batch Inference Pipeline CLI (Phase 7)"
    )
    parser.add_argument("--batch-size", type=int, default=100, help="Number of comments per batch (default 100)")
    parser.add_argument("--max-comments", type=int, default=None, help="Maximum total comments to process")
    parser.add_argument("--dry-run", action="store_true", help="Run inference without committing to database")
    parser.add_argument("--force-reprocess", action="store_true", help="Reset all comment statuses to pending before run")
    return parser.parse_args(args)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    args = parse_args()

    config = PipelineConfig(
        batch_size=args.batch_size,
        max_comments=args.max_comments,
        dry_run=args.dry_run,
        force_reprocess=args.force_reprocess,
    )

    service = PipelineService(config)
    result = service.run_pipeline()

    if result["status"] == "error":
        log.error("Pipeline run failed: %s", result["errors"])
        sys.exit(1)
    else:
        log.info("Pipeline run completed successfully.")


if __name__ == "__main__":
    main()
