"""Public Pulse YouTube Data API v3 Extraction Package (Phase 6).

Provides video discovery, comment fetching, privacy pseudonymization, and
service orchestration for extracting raw public discourse from YouTube.
"""

from public_pulse.extraction.comment_fetcher import CommentFetcher
from public_pulse.extraction.config import ExtractionConfig, ProgramConfig
from public_pulse.extraction.exceptions import (
    AuthError,
    CommentsDisabledError,
    ConfigurationError,
    ExtractionError,
    QuotaExceededError,
    RateLimitError,
    ResourceNotFoundError,
    YouTubeAPIError,
)
from public_pulse.extraction.parsers import hash_author_id
from public_pulse.extraction.service import ExtractionService
from public_pulse.extraction.video_discovery import VideoDiscovery
from public_pulse.extraction.youtube_client import YouTubeClient

__all__ = [
    "ExtractionConfig",
    "ProgramConfig",
    "ExtractionService",
    "YouTubeClient",
    "VideoDiscovery",
    "CommentFetcher",
    "hash_author_id",
    "ExtractionError",
    "YouTubeAPIError",
    "AuthError",
    "QuotaExceededError",
    "RateLimitError",
    "ResourceNotFoundError",
    "CommentsDisabledError",
    "ConfigurationError",
]
