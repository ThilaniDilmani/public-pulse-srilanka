"""Pipeline configuration model for batch inference (Phase 7)."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PipelineConfig:
    """Execution parameters for the production inference pipeline."""

    batch_size: int = 100
    max_comments: Optional[int] = None
    dry_run: bool = False
    force_reprocess: bool = False
