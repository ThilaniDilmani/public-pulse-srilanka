"""Configuration dataclass for Phase 10 Faithfulness Verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class VerifierConfig:
    """Configurable parameters for faithfulness verification."""

    verifier_method: str = "hybrid_nli_v1"       # Primary verification method
    verifier_model: str = "gemini-2.5-flash"      # LLM judge model name
    llm_provider: str = "gemini"                  # "gemini" or "mock"
    enable_stage1_rules: bool = True              # Enable deterministic rule checks
    enable_stage2_lexical: bool = True            # Enable lexical overlap checking
    enable_stage3_semantic: bool = True           # Enable LLM-as-judge semantic entailment
    numerical_tolerance: float = 0.15             # 15% tolerance for numerical claims (e.g. 60% vs 50%)
    use_jaccard_as_filter: bool = True            # Lexical overlap only used as supporting signal
    temperature: float = 0.0                      # Zero temperature for deterministic NLI judgements
    timeout_seconds: float = 60.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize config for logging and storage."""
        return {
            "verifier_method": self.verifier_method,
            "verifier_model": self.verifier_model,
            "llm_provider": self.llm_provider,
            "enable_stage1_rules": self.enable_stage1_rules,
            "enable_stage2_lexical": self.enable_stage2_lexical,
            "enable_stage3_semantic": self.enable_stage3_semantic,
            "numerical_tolerance": self.numerical_tolerance,
            "use_jaccard_as_filter": self.use_jaccard_as_filter,
            "temperature": self.temperature,
            "timeout_seconds": self.timeout_seconds,
        }
