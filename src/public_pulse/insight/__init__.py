"""Phase 9 Grounded LLM Insight Generation package for Public Pulse.

Exported classes:
  - InsightGeneratorConfig: Dataclass for configuration parameters.
  - Finding: Dataclass representing a grounded claim with evidence citations.
  - GeneratedInsight: Dataclass output produced by the insight generator.
  - LLMProvider: Protocol for LLM generation backends.
  - GeminiProvider: Google Gemini API implementation.
  - MockLLMProvider: Offline deterministic mock provider for unit testing.
  - GroundedInsightGenerator: Core DB-free generator.
  - InsightService: DB transaction & persistence orchestrator.
"""

from public_pulse.insight.config import InsightGeneratorConfig
from public_pulse.insight.generator import GroundedInsightGenerator
from public_pulse.insight.models import Finding, GeneratedInsight
from public_pulse.insight.prompt import build_prompt
from public_pulse.insight.provider import GeminiProvider, LLMProvider, MockLLMProvider
from public_pulse.insight.service import InsightService

__all__ = [
    "InsightGeneratorConfig",
    "Finding",
    "GeneratedInsight",
    "LLMProvider",
    "GeminiProvider",
    "MockLLMProvider",
    "GroundedInsightGenerator",
    "InsightService",
    "build_prompt",
]
