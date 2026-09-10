"""YouTube Data API v3 client with error handling, retries, and pagination (Phase 6).

Implements bounded retries with exponential backoff for transient errors.
Masks API credentials in all logs and error strings.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from public_pulse.extraction.exceptions import (
    AuthError,
    CommentsDisabledError,
    QuotaExceededError,
    RateLimitError,
    ResourceNotFoundError,
    YouTubeAPIError,
)

log = logging.getLogger(__name__)


def mask_sensitive_info(text: str, api_key: Optional[str] = None) -> str:
    """Strip or mask API key from error strings and log messages."""
    if not text:
        return ""
    if api_key and api_key in text:
        text = text.replace(api_key, "***API_KEY_MASKED***")
    return text


class YouTubeClient:
    """Client for YouTube Data API v3 operations."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        service: Optional[Resource] = None,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
    ):
        self.api_key = api_key
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        if service is not None:
            self._service = service
        elif api_key:
            self._service = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
        else:
            self._service = None

    def _get_service(self) -> Resource:
        if self._service is None:
            raise AuthError("YouTube client not initialized: missing API key or service instance.")
        return self._service

    def _execute_with_retry(self, request: Any) -> Dict[str, Any]:
        """Execute a googleapiclient request with exponential backoff for transient errors."""
        retries = 0
        while True:
            try:
                return request.execute()
            except HttpError as exc:
                status = exc.resp.status
                reason = str(exc)

                # Check for non-retryable errors
                if status == 401:
                    raise AuthError("Authentication failed: invalid YouTube API key.", status_code=401) from exc

                if status == 403:
                    content_str = str(exc.content) if hasattr(exc, "content") else ""
                    if "quotaExceeded" in content_str or "dailyLimitExceeded" in content_str or "quota" in reason.lower():
                        raise QuotaExceededError("YouTube API quota limit exceeded.", status_code=403, reason="quotaExceeded") from exc
                    if "commentsDisabled" in content_str or "disabled comments" in reason.lower():
                        raise CommentsDisabledError("Comments are disabled for this video.", status_code=403, reason="commentsDisabled") from exc
                    raise YouTubeAPIError(f"HTTP 403 Forbidden: {mask_sensitive_info(reason, self.api_key)}", status_code=403) from exc

                if status == 404:
                    raise ResourceNotFoundError("Requested YouTube resource not found.", status_code=404) from exc

                if status == 429:
                    raise RateLimitError("Rate limit exceeded (HTTP 429).", status_code=429) from exc

                # Check if retryable (transient 5xx server error)
                if status >= 500 and retries < self.max_retries:
                    retries += 1
                    sleep_time = self.backoff_factor ** retries
                    log.warning("Transient HTTP %d error. Retry %d/%d in %.1fs", status, retries, self.max_retries, sleep_time)
                    time.sleep(sleep_time)
                    continue

                raise YouTubeAPIError(
                    f"YouTube API HttpError {status}: {mask_sensitive_info(reason, self.api_key)}",
                    status_code=status,
                ) from exc
            except Exception as exc:
                if retries < self.max_retries:
                    retries += 1
                    sleep_time = self.backoff_factor ** retries
                    log.warning("Transient network error: %s. Retry %d/%d in %.1fs", exc, retries, self.max_retries, sleep_time)
                    time.sleep(sleep_time)
                    continue
                raise YouTubeAPIError(f"YouTube client exception: {mask_sensitive_info(str(exc), self.api_key)}") from exc

    def get_channel_metadata(self, channel_id: str) -> Dict[str, Any]:
        """Fetch metadata for a YouTube channel by ID."""
        service = self._get_service()
        req = service.channels().list(
            part="snippet,statistics",
            id=channel_id,
        )
        return self._execute_with_retry(req)

    def get_playlist_items(
        self,
        playlist_id: str,
        max_results: int = 50,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch items from a YouTube playlist."""
        service = self._get_service()
        kwargs: Dict[str, Any] = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": min(max_results, 50),
        }
        if page_token:
            kwargs["pageToken"] = page_token
        req = service.playlistItems().list(**kwargs)
        return self._execute_with_retry(req)

    def get_video_metadata(self, video_ids: List[str]) -> Dict[str, Any]:
        """Fetch video metadata for a list of video IDs (up to 50 per batch)."""
        if not video_ids:
            return {"items": []}
        service = self._get_service()
        req = service.videos().list(
            part="snippet,contentDetails,statistics",
            id=",".join(video_ids[:50]),
        )
        return self._execute_with_retry(req)

    def get_comment_threads(
        self,
        video_id: str,
        max_results: int = 100,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch comment threads for a video."""
        service = self._get_service()
        kwargs: Dict[str, Any] = {
            "part": "snippet,replies",
            "videoId": video_id,
            "maxResults": min(max_results, 100),
            "textFormat": "plainText",
        }
        if page_token:
            kwargs["pageToken"] = page_token
        req = service.commentThreads().list(**kwargs)
        return self._execute_with_retry(req)

    def search_channel_videos(
        self,
        channel_id: str,
        max_results: int = 50,
        page_token: Optional[str] = None,
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search videos within a specific channel (channel-based discovery fallback)."""
        service = self._get_service()
        kwargs: Dict[str, Any] = {
            "part": "snippet",
            "channelId": channel_id,
            "type": "video",
            "maxResults": min(max_results, 50),
            "order": "date",
        }
        if page_token:
            kwargs["pageToken"] = page_token
        if published_after:
            kwargs["publishedAfter"] = published_after
        if published_before:
            kwargs["publishedBefore"] = published_before

        req = service.search().list(**kwargs)
        return self._execute_with_retry(req)
