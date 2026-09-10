"""Exceptions for Public Pulse YouTube Extraction System (Phase 6)."""

from typing import Optional


class ExtractionError(Exception):
    """Base exception for all extraction errors."""


class YouTubeAPIError(ExtractionError):
    """Base exception for errors returned by YouTube Data API v3."""

    def __init__(self, message: str, status_code: Optional[int] = None, reason: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.reason = reason


class AuthError(YouTubeAPIError):
    """HTTP 401: Authentication error (e.g. invalid API key)."""


class QuotaExceededError(YouTubeAPIError):
    """HTTP 403: YouTube API quota limit reached."""


class RateLimitError(YouTubeAPIError):
    """HTTP 429: Too many requests."""


class ResourceNotFoundError(YouTubeAPIError):
    """HTTP 404: Channel, video, or playlist not found."""


class CommentsDisabledError(YouTubeAPIError):
    """HTTP 403: Comments are disabled for the specified video."""


class ConfigurationError(ExtractionError):
    """Missing or invalid configuration (e.g. missing API key)."""
