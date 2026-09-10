"""LLM provider abstraction layer supporting Google Gemini and Mock providers."""

from __future__ import annotations

import json
import logging
import os
import random
import time
from typing import Optional, Protocol, runtime_checkable

log = logging.getLogger(__name__)


@runtime_checkable
class LLMProvider(Protocol):
    """Abstract interface protocol for LLM text generation providers."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Execute LLM text generation request and return raw text response."""
        ...


class GeminiProvider:
    """Production LLM provider using official google-genai SDK for Gemini models."""

    def __init__(
        self,
        model_name: str = "gemini-3.6-flash",
        temperature: float = 0.1,
        max_output_tokens: int = 2048,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        retry_delay_seconds: float = 2.0,
        api_key: Optional[str] = None,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

        # Credentials: check GEMINI_API_KEY first, fallback to YOUTUBE_API_KEY
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("YOUTUBE_API_KEY")

    def _get_client():
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        from google import genai
        return genai.Client(api_key=self.api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Call Gemini API with exponential backoff for transient errors."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            response_mime_type="application/json",
        )

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                log.debug("Calling Gemini API (model=%s, attempt=%d)...", self.model_name, attempt)
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=user_prompt,
                    config=config,
                )
                if response.text:
                    return response.text
                raise RuntimeError("Empty response received from Gemini API.")
            except Exception as exc:
                last_exception = exc
                log.warning("Gemini API call failed (attempt %d/%d): %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    sleep_time = self.retry_delay_seconds * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                    time.sleep(sleep_time)

        raise RuntimeError(f"Gemini API request failed after {self.max_retries} attempts: {last_exception}") from last_exception


class MockLLMProvider:
    """Offline, deterministic mock LLM provider for zero-network unit testing."""

    def __init__(
        self,
        canned_response: Optional[str] = None,
        should_fail: bool = False,
        failure_exception: Optional[Exception] = None,
    ):
        self.canned_response = canned_response
        self.should_fail = should_fail
        self.failure_exception = failure_exception or RuntimeError("Mock LLM Provider failure simulation")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return deterministic JSON response without external network calls."""
        if self.should_fail:
            raise self.failure_exception

        if self.canned_response is not None:
            return self.canned_response

        # Default valid response structure
        default_payload = {
            "status": "success",
            "summary": "Among the analyzed comments from the retrieved evidence, public sentiment demonstrates critical feedback regarding service delivery.",
            "findings": [
                {
                    "finding_id": "F1",
                    "text": "Among the analyzed comments, several users raised economic concerns.",
                    "evidence_ids": [],
                    "confidence": "high",
                }
            ],
            "discourse_interpretation": "Retrieved comments reflect predominantly critical stance (STANCE_CRIT).",
            "limitations": "Findings are bounded to the retrieved sample and do not reflect population-wide opinions.",
            "uncertainty_note": "No significant ambiguity detected within this sample.",
        }
        return json.dumps(default_payload)
