"""Phase 10 Faithfulness Verification package for Public Pulse.

Exported classes:
  - VerifierConfig: Dataclass for configuration parameters.
  - ClaimVerification: Dataclass representing verification for an individual claim.
  - VerificationReport: Complete verification metrics report for an insight.
  - ClaimDecomposer: Deterministic clause splitter decomposing findings into atomic claims.
  - DeterministicChecker: Stage 1 rule checker for citations, numbers, and overclaims.
  - FaithfulnessVerifier: Core DB-free verification engine.
  - VerificationService: DB transaction & persistence orchestrator.
"""

from public_pulse.verification.checker import DeterministicChecker
from public_pulse.verification.config import VerifierConfig
from public_pulse.verification.decomposer import ClaimDecomposer
from public_pulse.verification.models import ClaimVerification, VerificationReport
from public_pulse.verification.service import VerificationService
from public_pulse.verification.verifier import FaithfulnessVerifier

__all__ = [
    "VerifierConfig",
    "ClaimVerification",
    "VerificationReport",
    "ClaimDecomposer",
    "DeterministicChecker",
    "FaithfulnessVerifier",
    "VerificationService",
]
