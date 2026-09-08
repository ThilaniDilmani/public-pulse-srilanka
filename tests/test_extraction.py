"""Unit tests for Phase 6 YouTube extraction system.

All tests use mocks — no live network requests or external dependencies required.
Validates config, API client retries/errors, parsers, discovery, comment fetcher,
service orchestration, privacy hashing, raw text preservation, shared channels,
and secret masking in log strings.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError
from httplib2 import Response

from public_pulse.database.models import (
    Channel,
    Comment,
    PipelineRun,
    PipelineRunStatusEnum,
    Program,
    Video,
)
from public_pulse.extraction.comment_fetcher import CommentFetcher
from public_pulse.extraction.config import ExtractionConfig, ProgramConfig
from public_pulse.extraction.exceptions import (
    AuthError,
    CommentsDisabledError,
    ConfigurationError,
    QuotaExceededError,
    RateLimitError,
    ResourceNotFoundError,
    YouTubeAPIError,
)
from public_pulse.extraction.parsers import (
    hash_author_id,
    parse_channel_item,
    parse_comment_item,
    parse_comment_thread_item,
    parse_video_item,
)
from public_pulse.extraction.service import ExtractionService
from public_pulse.extraction.video_discovery import VideoDiscovery
from public_pulse.extraction.youtube_client import YouTubeClient, mask_sensitive_info


# ===========================================================================
# 1. Config Tests
# ===========================================================================

def test_missing_api_key_raises_configuration_error(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        ExtractionConfig.load(require_api_key=True)


def test_valid_api_configuration_load(monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "TEST_FAKE_KEY_123")
    cfg = ExtractionConfig.load(require_api_key=True)
    assert cfg.api_key == "TEST_FAKE_KEY_123"
    assert len(cfg.programs) == 14


# ===========================================================================
# 2. Response Parser Tests
# ===========================================================================

def test_channel_parsing():
    raw_item = {
        "id": "UC_TEST_001",
        "snippet": {
            "title": "Test Channel Title",
            "description": "Test Description",
        },
        "statistics": {"subscriberCount": "125000"},
    }
    parsed = parse_channel_item(raw_item)
    assert parsed["youtube_channel_id"] == "UC_TEST_001"
    assert parsed["name"] == "Test Channel Title"
    assert parsed["subscriber_count"] == 125000
    assert "https://www.youtube.com/channel/UC_TEST_001" in parsed["channel_url"]


def test_video_parsing():
    raw_item = {
        "id": "VID_001",
        "snippet": {
            "title": "Test Video Title",
            "description": "Video Description",
            "publishedAt": "2026-09-01T12:00:00Z",
            "liveBroadcastContent": "none",
        },
        "contentDetails": {"duration": "PT15M30S"},
        "statistics": {"commentCount": "42"},
    }
    parsed = parse_video_item(raw_item)
    assert parsed["youtube_video_id"] == "VID_001"
    assert parsed["title"] == "Test Video Title"
    assert parsed["duration_seconds"] == 930
    assert parsed["comment_count"] == 42
    assert parsed["is_live"] is False


def test_comment_parsing_raw_text_preservation():
    raw_item = {
        "id": "COMM_001",
        "snippet": {
            "textOriginal": "මේක නම් හොඳයි ❤️ 😂 http://example.com #test",
            "authorChannelId": {"value": "UC_AUTHOR_999"},
            "likeCount": 15,
            "publishedAt": "2026-09-02T10:00:00Z",
        },
    }
    parsed = parse_comment_item(raw_item, video_id="VID_001")
    # Multilingual, emojis, punctuation, symbols, URLs MUST be preserved untouched in text_raw
    assert parsed["text_raw"] == "මේක නම් හොඳයි ❤️ 😂 http://example.com #test"
    assert parsed["text_clean"] == parsed["text_raw"]
    assert parsed["like_count"] == 15
    assert parsed["author_hash"] is not None


def test_reply_parsing():
    thread_item = {
        "snippet": {
            "topLevelComment": {
                "id": "TOP_001",
                "snippet": {
                    "textOriginal": "Top level comment",
                    "authorChannelId": {"value": "UC_AUTHOR_1"},
                },
            },
        },
        "replies": {
            "comments": [
                {
                    "id": "REPLY_001",
                    "snippet": {
                        "textOriginal": "First reply",
                        "authorChannelId": {"value": "UC_AUTHOR_2"},
                    },
                }
            ]
        },
    }
    top, replies = parse_comment_thread_item(thread_item, video_id="VID_001")
    assert top["youtube_comment_id"] == "TOP_001"
    assert top["is_reply"] is False

    assert len(replies) == 1
    assert replies[0]["youtube_comment_id"] == "REPLY_001"
    assert replies[0]["is_reply"] is True
    assert replies[0]["parent_comment_id"] == "TOP_001"


# ===========================================================================
# 3. Privacy Hashing Tests
# ===========================================================================

def test_author_privacy_hash():
    h1 = hash_author_id("UC_USER_123")
    h2 = hash_author_id("UC_USER_123")
    h3 = hash_author_id("UC_USER_456")

    assert h1 is not None
    assert h1 == h2  # Deterministic for same author ID
    assert h1 != h3  # Unique for different author ID
    assert "UC_USER_123" not in h1  # Raw user ID is not exposed

    # Test HMAC keyed hashing
    hmac1 = hash_author_id("UC_USER_123", secret_key="SECRET_KEY_1")
    hmac2 = hash_author_id("UC_USER_123", secret_key="SECRET_KEY_1")
    assert hmac1 == hmac2
    assert hmac1 != h1


# ===========================================================================
# 4. API Error Handling and Retry Tests
# ===========================================================================

def _make_http_error(status: int, reason: str = "Error", content: bytes = b""):
    resp = Response({"status": status, "reason": reason})
    return HttpError(resp, content=content)


def test_401_auth_error_raises_auth_exception():
    mock_service = MagicMock()
    mock_req = MagicMock()
    mock_req.execute.side_effect = _make_http_error(401, "Unauthorized")
    mock_service.channels().list.return_value = mock_req

    client = YouTubeClient(api_key="INVALID_KEY", service=mock_service)
    with pytest.raises(AuthError):
        client.get_channel_metadata("UC_123")


def test_403_quota_exceeded_error_raises_quota_exception():
    mock_service = MagicMock()
    mock_req = MagicMock()
    mock_req.execute.side_effect = _make_http_error(403, "Quota Exceeded", content=b"quotaExceeded")
    mock_service.playlistItems().list.return_value = mock_req

    client = YouTubeClient(service=mock_service)
    with pytest.raises(QuotaExceededError):
        client.get_playlist_items("PL_123")


def test_403_comments_disabled_error():
    mock_service = MagicMock()
    mock_req = MagicMock()
    mock_req.execute.side_effect = _make_http_error(403, "Comments Disabled", content=b"commentsDisabled")
    mock_service.commentThreads().list.return_value = mock_req

    client = YouTubeClient(service=mock_service)
    with pytest.raises(CommentsDisabledError):
        client.get_comment_threads("VID_123")


def test_404_resource_not_found():
    mock_service = MagicMock()
    mock_req = MagicMock()
    mock_req.execute.side_effect = _make_http_error(404, "Not Found")
    mock_service.videos().list.return_value = mock_req

    client = YouTubeClient(service=mock_service)
    with pytest.raises(ResourceNotFoundError):
        client.get_video_metadata(["VID_999"])


def test_429_rate_limit_error():
    mock_service = MagicMock()
    mock_req = MagicMock()
    mock_req.execute.side_effect = _make_http_error(429, "Rate Limit")
    mock_service.search().list.return_value = mock_req

    client = YouTubeClient(service=mock_service)
    with pytest.raises(RateLimitError):
        client.search_channel_videos("UC_123")


def test_retryable_500_error_succeeds_on_retry():
    mock_service = MagicMock()
    mock_req = MagicMock()

    # First call fails with 503, second call succeeds
    mock_req.execute.side_effect = [
        _make_http_error(503, "Service Unavailable"),
        {"items": [{"id": "UC_123", "snippet": {"title": "Channel"}}]},
    ]
    mock_service.channels().list.return_value = mock_req

    with patch("time.sleep", return_value=None):
        client = YouTubeClient(service=mock_service, max_retries=2)
        res = client.get_channel_metadata("UC_123")
        assert res["items"][0]["id"] == "UC_123"
        assert mock_req.execute.call_count == 2


def test_non_retryable_error_fails_immediately():
    mock_service = MagicMock()
    mock_req = MagicMock()
    mock_req.execute.side_effect = _make_http_error(400, "Bad Request")
    mock_service.channels().list.return_value = mock_req

    client = YouTubeClient(service=mock_service)
    with pytest.raises(YouTubeAPIError):
        client.get_channel_metadata("UC_BAD")
    assert mock_req.execute.call_count == 1


# ===========================================================================
# 5. Discovery & Fetching Tests
# ===========================================================================

def test_playlist_based_discovery():
    mock_client = MagicMock()
    mock_client.get_playlist_items.return_value = {
        "items": [
            {"snippet": {"resourceId": {"videoId": "VID_PL_1"}}},
            {"snippet": {"resourceId": {"videoId": "VID_PL_2"}}},
        ]
    }
    mock_client.get_video_metadata.return_value = {
        "items": [
            {"id": "VID_PL_1", "snippet": {"title": "Episode 1", "publishedAt": "2026-09-01T00:00:00Z"}},
            {"id": "VID_PL_2", "snippet": {"title": "Episode 2", "publishedAt": "2026-09-02T00:00:00Z"}},
        ]
    }

    discovery = VideoDiscovery(mock_client)
    prog = ProgramConfig(
        program_name="Test Playlist Program",
        channel_id="UC_123",
        playlist_id="PL_123",
    )
    discovered = discovery.discover_for_program(prog)

    assert len(discovered) == 2
    assert discovered[0].video_id == "VID_PL_1"
    assert discovered[0].discovery_method == "PLAYLIST"
    assert discovered[0].is_matched is True


def test_program_without_playlist_candidate_discovery():
    mock_client = MagicMock()
    mock_client.search_channel_videos.return_value = {
        "items": [
            {"id": {"videoId": "VID_CH_1"}},
            {"id": {"videoId": "VID_CH_2"}},
        ]
    }
    mock_client.get_video_metadata.return_value = {
        "items": [
            {"id": "VID_CH_1", "snippet": {"title": "Truth with Chamuditha Special Episode", "publishedAt": "2026-09-01T00:00:00Z"}},
            {"id": "VID_CH_2", "snippet": {"title": "Unrelated Vlog Video", "publishedAt": "2026-09-02T00:00:00Z"}},
        ]
    }

    discovery = VideoDiscovery(mock_client)
    prog = ProgramConfig(
        program_name="Truth with Chamuditha",
        channel_id="UC_CHAMUDITHA",
        playlist_id=None,  # No playlist
        keywords=["Chamuditha"],
    )
    discovered = discovery.discover_for_program(prog)

    # Should only discover VID_CH_1 because title matches keyword "Chamuditha".
    # VID_CH_2 is skipped as unmatched and not silently assigned!
    assert len(discovered) == 1
    assert discovered[0].video_id == "VID_CH_1"
    assert discovered[0].discovery_method == "CHANNEL_TITLE_MATCH"


def test_comments_disabled_handled_gracefully():
    mock_client = MagicMock()
    mock_client.get_comment_threads.side_effect = CommentsDisabledError("Comments disabled")

    fetcher = CommentFetcher(mock_client)
    comments = fetcher.fetch_comments_for_video("VID_DISABLED")
    assert comments == []


def test_empty_api_responses():
    mock_client = MagicMock()
    mock_client.get_playlist_items.return_value = {"items": []}
    discovery = VideoDiscovery(mock_client)
    prog = ProgramConfig("Empty Program", "UC_EMPTY", "PL_EMPTY")
    discovered = discovery.discover_for_program(prog)
    assert discovered == []


def test_pagination_in_comment_fetcher():
    mock_client = MagicMock()
    mock_client.get_comment_threads.side_effect = [
        {
            "items": [
                {"id": "C1", "snippet": {"topLevelComment": {"id": "C1", "snippet": {"textOriginal": "Page 1"}}}}
            ],
            "nextPageToken": "TOKEN_PAGE_2",
        },
        {
            "items": [
                {"id": "C2", "snippet": {"topLevelComment": {"id": "C2", "snippet": {"textOriginal": "Page 2"}}}}
            ],
        },
    ]

    fetcher = CommentFetcher(mock_client)
    comments = fetcher.fetch_comments_for_video("VID_PAGED")
    assert len(comments) == 2
    assert comments[0]["text_raw"] == "Page 1"
    assert comments[1]["text_raw"] == "Page 2"
    assert mock_client.get_comment_threads.call_count == 2


# ===========================================================================
# 6. Service & Database Integration Tests (SQLite in-memory via fixture)
# ===========================================================================

def test_shared_channel_creates_one_channel_and_multiple_programs(db):
    """Channel UCckltLEhFLv8Xz_lQhYfwmg must produce 1 Channel row and multiple Program rows."""
    programs_cfg = [
        ProgramConfig("Hiru Salakuna (Hiru)", "UCckltLEhFLv8Xz_lQhYfwmg", "PL1"),
        ProgramConfig("Hiru Balaya (Hiru)", "UCckltLEhFLv8Xz_lQhYfwmg", "PL2"),
        ProgramConfig("Paththare visthare (Hiru News)", "UCckltLEhFLv8Xz_lQhYfwmg", "PL3"),
        ProgramConfig("Hiru news 6.55pm (Hiru newa)", "UCckltLEhFLv8Xz_lQhYfwmg", "PL4"),
    ]

    mock_client = MagicMock()
    mock_client.get_channel_metadata.return_value = {
        "items": [{"id": "UCckltLEhFLv8Xz_lQhYfwmg", "snippet": {"title": "Hiru News Channel"}}]
    }
    mock_client.get_playlist_items.return_value = {"items": []}

    config = ExtractionConfig(api_key="KEY", programs=programs_cfg)
    service = ExtractionService(config, client=mock_client)
    stats = service.run_extraction(db=db)

    assert stats["programs_processed"] == 4

    # Verify Database state
    channels = db.query(Channel).all()
    programs = db.query(Program).all()

    assert len(channels) == 1
    assert channels[0].youtube_channel_id == "UCckltLEhFLv8Xz_lQhYfwmg"

    assert len(programs) == 4
    assert {p.name for p in programs} == {
        "Hiru Salakuna (Hiru)",
        "Hiru Balaya (Hiru)",
        "Paththare visthare (Hiru News)",
        "Hiru news 6.55pm (Hiru newa)",
    }
    assert all(p.channel_id == channels[0].id for p in programs)


def test_idempotent_duplicate_extraction(db):
    """Running extraction twice on identical data produces ZERO duplicates."""
    prog_cfg = ProgramConfig("Test Idempotency", "UC_IDEM", "PL_IDEM")
    mock_client = MagicMock()
    mock_client.get_channel_metadata.return_value = {
        "items": [{"id": "UC_IDEM", "snippet": {"title": "Channel"}}]
    }
    mock_client.get_playlist_items.return_value = {
        "items": [{"snippet": {"resourceId": {"videoId": "VID_IDEM"}}}]
    }
    mock_client.get_video_metadata.return_value = {
        "items": [{"id": "VID_IDEM", "snippet": {"title": "Video 1"}}]
    }
    mock_client.get_comment_threads.return_value = {
        "items": [
            {"id": "COMM_IDEM", "snippet": {"topLevelComment": {"id": "COMM_IDEM", "snippet": {"textOriginal": "Raw Comment"}}}}
        ]
    }

    config = ExtractionConfig(api_key="KEY", programs=[prog_cfg])
    service = ExtractionService(config, client=mock_client)

    # First run
    stats1 = service.run_extraction(db=db)
    assert stats1["comments_inserted"] == 1
    assert stats1["comments_updated"] == 0

    # Second run (exact same data)
    stats2 = service.run_extraction(db=db)
    assert stats2["comments_inserted"] == 0
    assert stats2["comments_updated"] == 1  # Updated, not duplicated!

    # DB verify
    assert db.query(Channel).count() == 1
    assert db.query(Program).count() == 1
    assert db.query(Video).count() == 1
    assert db.query(Comment).count() == 1


def test_pipeline_run_success_tracking(db):
    prog_cfg = ProgramConfig("Pipeline Track Program", "UC_PIPE", "PL_PIPE")
    mock_client = MagicMock()
    mock_client.get_channel_metadata.return_value = {"items": []}
    mock_client.get_playlist_items.return_value = {"items": []}

    config = ExtractionConfig(api_key="KEY", programs=[prog_cfg])
    service = ExtractionService(config, client=mock_client)
    service.run_extraction(db=db)

    runs = db.query(PipelineRun).all()
    assert len(runs) == 1
    assert runs[0].run_type == "youtube_extraction"
    assert runs[0].status == PipelineRunStatusEnum.success
    assert runs[0].finished_at is not None


def test_pipeline_run_failure_tracking(db):
    prog_cfg = ProgramConfig("Fail Program", "UC_FAIL", "PL_FAIL")
    mock_client = MagicMock()
    mock_client.get_channel_metadata.return_value = {"items": []}
    mock_client.get_playlist_items.side_effect = Exception("Fatal API Failure")

    config = ExtractionConfig(api_key="KEY", programs=[prog_cfg])
    service = ExtractionService(config, client=mock_client)
    stats = service.run_extraction(db=db)

    assert stats["status"] == "error"
    runs = db.query(PipelineRun).all()
    assert len(runs) == 1
    assert runs[0].status == PipelineRunStatusEnum.error
    assert "Fatal API Failure" in runs[0].error_message



def test_dry_run_mode(db):
    prog_cfg = ProgramConfig("Dry Run Program", "UC_DRY", "PL_DRY")
    mock_client = MagicMock()
    mock_client.get_channel_metadata.return_value = {"items": []}
    mock_client.get_playlist_items.return_value = {"items": []}

    config = ExtractionConfig(api_key="KEY", programs=[prog_cfg], dry_run=True)
    service = ExtractionService(config, client=mock_client)
    stats = service.run_extraction(db=db)

    assert stats["run_id"] == "dry_run"
    # No PipelineRun rows inserted in DB during dry_run
    assert db.query(PipelineRun).count() == 0


def test_api_key_never_appears_in_logs_or_masked_output():
    secret_key = "MY_SUPER_SECRET_YOUTUBE_API_KEY_999"
    raw_error = f"HttpError calling https://www.googleapis.com/youtube/v3/channels?key={secret_key}"
    masked = mask_sensitive_info(raw_error, secret_key)

    assert secret_key not in masked
    assert "***API_KEY_MASKED***" in masked
