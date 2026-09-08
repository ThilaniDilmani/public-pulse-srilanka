"""Public Pulse database package.

Exports the ORM base, key model classes, session utilities, and
the repository layer so callers only need one import path.

Example:
    from public_pulse.database import Channel, Comment, get_db, upsert_channel
"""

from public_pulse.database.models import (
    Annotation,
    Base,
    Channel,
    Comment,
    Evidence,
    EvidenceSet,
    Insight,
    LayerEnum,
    LayerPrediction,
    ModelVersion,
    PipelineRun,
    PipelineRunStatusEnum,
    ProcessingStatusEnum,
    Program,
    VerificationResult,
    Video,
    JobRecord,
)

__all__ = [
    # Base
    "Base",
    # Enums
    "LayerEnum",
    "ProcessingStatusEnum",
    "PipelineRunStatusEnum",
    # Models
    "Channel",
    "Program",
    "Video",
    "Comment",
    "ModelVersion",
    "LayerPrediction",
    "PipelineRun",
    "Annotation",
    "Evidence",
    "EvidenceSet",
    "Insight",
    "VerificationResult",
    "JobRecord",
]

