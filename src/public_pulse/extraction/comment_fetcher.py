"""Comment fetcher for YouTube videos (Phase 6).

Fetches top-level comment threads and nested replies with pagination.
Handles CommentsDisabledError gracefully.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from public_pulse.extraction.exceptions import CommentsDisabledError
from public_pulse.extraction.parsers import parse_comment_thread_item
from public_pulse.extraction.youtube_client import YouTubeClient

log = logging.getLogger(__name__)


class CommentFetcher:
    """Fetches comments and replies for a YouTube video."""

    def __init__(self, client: YouTubeClient, secret_key: Optional[str] = None):
        self.client = client
        self.secret_key = secret_key

    def fetch_comments_for_video(
        self,
        video_id: str,
        limit_comments: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all top-level comments and replies for a video up to limit_comments.

        Returns a list of parsed comment dictionaries ready for repository insertion.
        """
        all_comments: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        try:
            while True:
                response = self.client.get_comment_threads(
                    video_id=video_id,
                    max_results=100,
                    page_token=page_token,
                )
                items = response.get("items", [])
                if not items:
                    break

                for thread_item in items:
                    top_comment, replies = parse_comment_thread_item(
                        thread_item,
                        video_id=video_id,
                        secret_key=self.secret_key,
                    )

                    all_comments.append(top_comment)
                    if limit_comments and len(all_comments) >= limit_comments:
                        return all_comments[:limit_comments]

                    for reply in replies:
                        all_comments.append(reply)
                        if limit_comments and len(all_comments) >= limit_comments:
                            return all_comments[:limit_comments]

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        except CommentsDisabledError:
            log.info("Comments are disabled for video %s — skipping comment extraction.", video_id)
            return []

        return all_comments
