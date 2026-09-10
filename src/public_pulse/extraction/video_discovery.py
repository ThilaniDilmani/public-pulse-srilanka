"""Video discovery strategies for YouTube programs (Phase 6).

Implements playlist-based discovery and candidate channel-based discovery.
Enforces that programs without playlists do not automatically consume every video
on a channel, and preserves discovery provenance (PLAYLIST, CHANNEL_TITLE_MATCH, etc.).
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from public_pulse.extraction.config import ProgramConfig
from public_pulse.extraction.parsers import parse_video_item
from public_pulse.extraction.youtube_client import YouTubeClient

log = logging.getLogger(__name__)


@dataclass
class DiscoveredVideo:
    """Video item discovered for a program with discovery provenance."""

    program_name: str
    channel_id: str
    video_id: str
    metadata: Dict[str, Any]
    discovery_method: str  # PLAYLIST, CHANNEL_TITLE_MATCH, CHANNEL_DATE_MATCH, MANUAL
    is_matched: bool = True
    match_reason: str = ""


class VideoDiscovery:
    """Discovers videos for a target program using YouTube Data API v3."""

    def __init__(self, client: YouTubeClient):
        self.client = client

    def discover_for_program(
        self,
        program: ProgramConfig,
        limit_videos: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[DiscoveredVideo]:
        """Discover videos for a program using its configured strategy."""
        if program.playlist_id:
            log.info("Discovering videos via PLAYLIST for %r (Playlist: %s)", program.program_name, program.playlist_id)
            return self._discover_via_playlist(program, limit_videos, since, until)
        else:
            log.info("Discovering candidate videos via CHANNEL for %r (Channel: %s)", program.program_name, program.channel_id)
            return self._discover_via_channel(program, limit_videos, since, until)

    def _discover_via_playlist(
        self,
        program: ProgramConfig,
        limit_videos: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[DiscoveredVideo]:
        """Playlist-based discovery: authoritative program-video association."""
        discovered: List[DiscoveredVideo] = []
        page_token: Optional[str] = None

        while True:
            response = self.client.get_playlist_items(
                playlist_id=program.playlist_id,
                max_results=50,
                page_token=page_token,
            )
            if not isinstance(response, dict):
                break
            items = response.get("items", [])
            if not isinstance(items, list) or not items:
                break

            # Extract video IDs
            video_ids = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                snippet = item.get("snippet", {})
                resource_id = snippet.get("resourceId", {})
                vid = resource_id.get("videoId") or item.get("contentDetails", {}).get("videoId")
                if vid and isinstance(vid, str):
                    video_ids.append(vid)

            # Fetch full video metadata
            if video_ids:
                video_response = self.client.get_video_metadata(video_ids)
                video_items = video_response.get("items", []) if isinstance(video_response, dict) else []
                for v_item in video_items:
                    if not isinstance(v_item, dict):
                        continue
                    meta = parse_video_item(v_item)
                    # Optional date filter check
                    if since and meta.get("published_at") and meta["published_at"].isoformat() < since:
                        continue
                    if until and meta.get("published_at") and meta["published_at"].isoformat() > until:
                        continue

                    discovered.append(
                        DiscoveredVideo(
                            program_name=program.program_name,
                            channel_id=program.channel_id,
                            video_id=meta["youtube_video_id"],
                            metadata=meta,
                            discovery_method="PLAYLIST",
                            is_matched=True,
                            match_reason="Authoritative playlist membership",
                        )
                    )
                    if limit_videos and len(discovered) >= limit_videos:
                        return discovered

            next_token = response.get("nextPageToken")
            if not next_token or not isinstance(next_token, str) or next_token == page_token:
                break
            page_token = next_token

        return discovered


    def _discover_via_channel(
        self,
        program: ProgramConfig,
        limit_videos: Optional[int] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> List[DiscoveredVideo]:
        """Channel-based candidate discovery: filters videos using keywords/title matching."""
        discovered: List[DiscoveredVideo] = []
        page_token: Optional[str] = None

        while True:
            response = self.client.search_channel_videos(
                channel_id=program.channel_id,
                max_results=50,
                page_token=page_token,
                published_after=since,
                published_before=until,
            )
            if not isinstance(response, dict):
                break
            items = response.get("items", [])
            if not isinstance(items, list) or not items:
                break

            video_ids = [
                it["id"]["videoId"]
                for it in items
                if isinstance(it, dict) and isinstance(it.get("id"), dict) and isinstance(it["id"].get("videoId"), str)
            ]

            if video_ids:
                video_response = self.client.get_video_metadata(video_ids)
                video_items = video_response.get("items", []) if isinstance(video_response, dict) else []

                for v_item in video_items:
                    if not isinstance(v_item, dict):
                        continue
                    meta = parse_video_item(v_item)
                    matched, method, reason = self._match_channel_video(meta, program)

                    if matched:
                        discovered.append(
                            DiscoveredVideo(
                                program_name=program.program_name,
                                channel_id=program.channel_id,
                                video_id=meta["youtube_video_id"],
                                metadata=meta,
                                discovery_method=method,
                                is_matched=True,
                                match_reason=reason,
                            )
                        )
                    else:
                        log.info(
                            "Skipping unmatched channel video %s for program %r: %s",
                            meta.get("youtube_video_id"),
                            program.program_name,
                            reason,
                        )

                    if limit_videos and len(discovered) >= limit_videos:
                        return discovered

            next_token = response.get("nextPageToken")
            if not next_token or not isinstance(next_token, str) or next_token == page_token:
                break
            page_token = next_token

        return discovered


    def _match_channel_video(
        self, meta: Dict[str, Any], program: ProgramConfig
    ) -> Tuple[bool, str, str]:
        """Check whether a video from a channel matches a program without a playlist."""
        title = (meta.get("title") or "").lower()
        desc = (meta.get("description") or "").lower()

        # Check explicit keywords
        for kw in program.keywords:
            kw_lower = kw.lower()
            if kw_lower in title or kw_lower in desc:
                return True, "CHANNEL_TITLE_MATCH", f"Matched keyword: '{kw}'"

        # Check program name match
        prog_clean = program.program_name.lower()
        if prog_clean in title or prog_clean in desc:
            return True, "CHANNEL_TITLE_MATCH", f"Matched program name: '{program.program_name}'"

        # Fallback: if no keywords defined, treat all channel videos as candidate with date match
        if not program.keywords:
            return True, "CHANNEL_DATE_MATCH", "Channel-level discovery (no keywords specified)"

        return False, "UNMATCHED", "Title/description does not contain program keywords"
