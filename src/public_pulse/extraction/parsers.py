"""Response parsers and privacy hashing for YouTube API data (Phase 6).

Preserves exact raw text for `text_raw` without any NLP preprocessing.
Applies HMAC-SHA256 pseudonymization for author channel IDs.
"""

import hashlib
import hmac
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# ISO-8601 duration pattern (e.g. PT1H2M10S)
ISO_DURATION_REGEX = re.compile(r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?")


def hash_author_id(author_channel_id: Optional[str], secret_key: Optional[str] = None) -> Optional[str]:
    """Generate a stable pseudonymous author_hash from YouTube author channel ID.

    Uses HMAC-SHA256 if a secret_key is provided, or SHA-256 as fallback.
    Never exposes raw channel IDs or user names in analytics.
    """
    if not author_channel_id:
        return None

    clean_id = author_channel_id.strip()
    if not clean_id:
        return None

    if secret_key:
        key_bytes = secret_key.encode("utf-8")
        msg_bytes = clean_id.encode("utf-8")
        return hmac.new(key_bytes, msg_bytes, hashlib.sha256).hexdigest()
    else:
        return hashlib.sha256(clean_id.encode("utf-8")).hexdigest()


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 timestamp from YouTube API into UTC datetime object."""
    if not dt_str:
        return None
    try:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str).astimezone(timezone.utc)
    except Exception as exc:
        log.warning("Failed to parse datetime %r: %s", dt_str, exc)
        return None


def parse_iso_duration(duration_str: Optional[str]) -> Optional[int]:
    """Parse ISO-8601 duration string (e.g. PT1H15M30S) into integer total seconds."""
    if not duration_str:
        return None
    try:
        match = ISO_DURATION_REGEX.match(duration_str)
        if not match:
            return None
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        seconds = int(match.group("seconds") or 0)
        return hours * 3600 + minutes * 60 + seconds
    except Exception:
        return None



def parse_channel_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Extract channel attributes from a YouTube API channels.list resource item."""
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})

    channel_id = item.get("id") or snippet.get("channelId")
    sub_count_str = stats.get("subscriberCount")
    sub_count = int(sub_count_str) if sub_count_str is not None else None

    return {
        "youtube_channel_id": channel_id,
        "name": snippet.get("title", ""),
        "channel_url": f"https://www.youtube.com/channel/{channel_id}" if channel_id else None,
        "description": snippet.get("description"),
        "subscriber_count": sub_count,
    }


def parse_video_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Extract video attributes from a YouTube API videos.list resource item."""
    snippet = item.get("snippet", {})
    content_details = item.get("contentDetails", {})
    stats = item.get("statistics", {})

    video_id = item.get("id")
    if isinstance(video_id, dict):
        video_id = video_id.get("videoId")

    comment_count_str = stats.get("commentCount")
    comment_count = int(comment_count_str) if comment_count_str is not None else None

    live_broadcast = snippet.get("liveBroadcastContent")
    is_live = live_broadcast in ("live", "upcoming")

    return {
        "youtube_video_id": video_id,
        "title": snippet.get("title"),
        "description": snippet.get("description"),
        "published_at": parse_iso_datetime(snippet.get("publishedAt")),
        "duration_seconds": parse_iso_duration(content_details.get("duration")),
        "is_live": is_live,
        "comment_count": comment_count,
    }


def parse_comment_item(
    item: Dict[str, Any],
    video_id: str,
    secret_key: Optional[str] = None,
    is_reply: bool = False,
    parent_comment_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract comment attributes from a single comment snippet.

    CRITICAL: `text_raw` receives the unmodified raw textDisplay/textOriginal from YouTube.
    No NLP cleaning is performed.
    """
    snippet = item.get("snippet", {})
    author_channel = snippet.get("authorChannelId", {})
    author_channel_id = author_channel.get("value") if isinstance(author_channel, dict) else author_channel

    # Prefer textOriginal if present, fallback to textDisplay
    raw_text = snippet.get("textOriginal") or snippet.get("textDisplay") or ""

    comment_id = item.get("id")

    return {
        "youtube_comment_id": comment_id,
        "youtube_video_id": video_id,
        "parent_comment_id": parent_comment_id,
        "text_raw": raw_text,
        "text_clean": raw_text,  # Phase 6 stores raw text without NLP cleaning; Phase 7 cleans later
        "author_hash": hash_author_id(author_channel_id, secret_key),
        "like_count": int(snippet.get("likeCount", 0)),
        "reply_count": int(snippet.get("totalReplyCount", 0)) if not is_reply else 0,
        "posted_at": parse_iso_datetime(snippet.get("publishedAt")),
        "is_reply": is_reply,
    }


def parse_comment_thread_item(
    thread_item: Dict[str, Any],
    video_id: str,
    secret_key: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Parse a commentThreads resource item into (top_level_comment, [replies])."""
    snippet = thread_item.get("snippet", {})
    top_comment_resource = snippet.get("topLevelComment", {})
    
    top_comment = parse_comment_item(
        top_comment_resource,
        video_id=video_id,
        secret_key=secret_key,
        is_reply=False,
        parent_comment_id=None,
    )

    replies = []
    replies_resource = thread_item.get("replies", {})
    comments_list = replies_resource.get("comments", [])
    for reply_item in comments_list:
        parsed_reply = parse_comment_item(
            reply_item,
            video_id=video_id,
            secret_key=secret_key,
            is_reply=True,
            parent_comment_id=top_comment["youtube_comment_id"],
        )
        replies.append(parsed_reply)

    return top_comment, replies
