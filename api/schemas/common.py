"""Common API response schemas (Phase 11)."""

from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ErrorOut(BaseModel):
    """Standardized API error response schema."""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated list response schema."""
    items: List[T]
    total: int
    limit: int
    offset: int
