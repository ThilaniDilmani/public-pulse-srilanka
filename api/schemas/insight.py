"""Insight Pydantic schemas (Phase 11)."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel


class InsightGenerationIn(BaseModel):
    evidence_set_id: str
    program_id: Optional[str] = None


class FindingOut(BaseModel):
    finding_id: str
    text: str
    evidence_ids: List[str]
    confidence: str


class InsightOut(BaseModel):
    insight_id: str
    evidence_set_id: Optional[str] = None
    program_id: Optional[str] = None
    insight_type: str
    generation_status: str
    summary: Optional[str] = None
    findings: List[FindingOut] = []
    discourse_interpretation: Optional[str] = None
    limitations: Optional[str] = None
    uncertainty_note: Optional[str] = None
    llm_provider: str
    llm_model: str
    prompt_version: str
    generated_at: str
    evidence_count_used: int = 0
    stance_distribution: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None


class JobStatusOut(BaseModel):
    job_id: str
    job_type: str
    status: str  # "pending" | "running" | "completed" | "error"
    reference_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
