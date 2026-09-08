"""Batch processor engine for production inference pipeline (Phase 7).

Coordinates comment text preparation, cascade prediction execution, model version
association per layer, and bulk DB persistence using the Phase 5B repository layer.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from public_pulse.database.models import Comment, LayerEnum, ModelVersion, ProcessingStatusEnum
from public_pulse.database.repository import insert_predictions
from public_pulse.inference.cascade import InferenceCascade

log = logging.getLogger(__name__)


class BatchProcessor:
    """Processes batches of comments through the InferenceCascade and persists predictions."""

    def __init__(
        self,
        cascade: InferenceCascade,
        model_version_map: Dict[LayerEnum, ModelVersion],
        dry_run: bool = False,
    ):
        self.cascade = cascade
        self.model_version_map = model_version_map
        self.dry_run = dry_run

    def process_batch(self, db: Session, comments: List[Comment]) -> Dict[str, int]:
        """Process a list of Comment objects through inference cascade and persist results.

        Performs:
          1. Raw text extraction & clean_text variant generation
          2. Layer 1 inference (VALID vs NOISE)
          3. Early exit for NOISE comments (skips Layer 2/4 execution)
          4. Layer 2 & 4 inference for VALID comments
          5. Prediction persistence & comment status update via repository
          6. Transaction commit per batch
        """
        if not comments:
            return {"processed": 0, "valid": 0, "noise": 0}

        raw_texts = [c.text_raw for c in comments]
        cascade_results = self.cascade.predict_batch(raw_texts)

        l1_mv = self.model_version_map[LayerEnum.layer1]
        l2_mv = self.model_version_map[LayerEnum.layer2]
        l4_mv = self.model_version_map[LayerEnum.layer4]

        batch_stats = {"processed": len(comments), "valid": 0, "noise": 0}

        for comment, result in zip(comments, cascade_results):
            # Store Phase 3 generated text_clean on comment model
            comment.text_clean = result.text_clean

            # Layer 1 prediction
            l1_pred = {
                "layer": "layer1",
                "label": result.layer1.label,
                "label_id": result.layer1.label_id,
                "confidence": result.layer1.confidence,
            }

            if result.is_noise:
                batch_stats["noise"] += 1
                if not self.dry_run:
                    comment.processing_status = ProcessingStatusEnum.noise_exit
                    insert_predictions(
                        db,
                        comment_id=comment.id,
                        model_version_id=l1_mv.id,
                        predictions=[l1_pred],
                    )
            else:
                batch_stats["valid"] += 1
                if not self.dry_run:
                    comment.processing_status = ProcessingStatusEnum.scored
                    # Insert Layer 1 prediction
                    insert_predictions(
                        db,
                        comment_id=comment.id,
                        model_version_id=l1_mv.id,
                        predictions=[l1_pred],
                    )

                    # Insert Layer 2 prediction if present
                    if result.layer2:
                        l2_pred = {
                            "layer": "layer2",
                            "label": result.layer2.label,
                            "label_id": result.layer2.label_id,
                            "confidence": result.layer2.confidence,
                        }
                        insert_predictions(
                            db,
                            comment_id=comment.id,
                            model_version_id=l2_mv.id,
                            predictions=[l2_pred],
                        )

                    # Insert Layer 4 prediction if present
                    if result.layer4:
                        l4_pred = {
                            "layer": "layer4",
                            "label": result.layer4.label,
                            "label_id": result.layer4.label_id,
                            "confidence": result.layer4.confidence,
                        }
                        insert_predictions(
                            db,
                            comment_id=comment.id,
                            model_version_id=l4_mv.id,
                            predictions=[l4_pred],
                        )

        if not self.dry_run:
            db.commit()

        log.debug(
            "Batch processed: %d total (%d valid, %d noise)",
            batch_stats["processed"],
            batch_stats["valid"],
            batch_stats["noise"],
        )

        return batch_stats
