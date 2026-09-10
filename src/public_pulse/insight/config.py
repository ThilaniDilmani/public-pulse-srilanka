import os
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class InsightGeneratorConfig:
    """Configurable execution parameters for grounded LLM insight generation."""

    llm_provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "gemini"))
    llm_model: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "gemini-3.6-flash"))
    prompt_version: str = "v1.0"                # Versioned prompt strategy
    temperature: float = 0.1                    # Low temperature for grounded stability
    max_output_tokens: int = 2048               # Max tokens for response
    timeout_seconds: float = 60.0               # Call timeout in seconds
    max_retries: int = 3                        # Retries for transient failures
    retry_delay_seconds: float = 2.0            # Base backoff delay
    min_evidence_threshold: int = 1             # Minimum evidence items required

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration parameters for provenance logging."""
        return {
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "prompt_version": self.prompt_version,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "min_evidence_threshold": self.min_evidence_threshold,
        }
