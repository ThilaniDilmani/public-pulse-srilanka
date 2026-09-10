#!/usr/bin/env python3
"""Smoke test for YouTube Data API extraction configuration (Phase 6).

Verifies YOUTUBE_API_KEY environment variable, loads target programs configuration
from configs/programs.yaml, and executes a 1-video test call to confirm connectivity.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from public_pulse.extraction.config import ExtractionConfig
from public_pulse.extraction.youtube_client import YouTubeClient
from public_pulse.extraction.video_discovery import VideoDiscovery

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("smoke_test_youtube")


def main() -> int:
    print("=" * 72)
    print("Public Pulse — YouTube Extraction Smoke Test")
    print("=" * 72)

    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("[FAIL] YOUTUBE_API_KEY is missing or empty in .env or environment.")
        return 1

    print(f"[OK] YOUTUBE_API_KEY found ({api_key[:6]}...{api_key[-4:]})")

    try:
        config = ExtractionConfig.load(require_api_key=True)
        print(f"[OK] Loaded {len(config.programs)} target programs from configs/programs.yaml")
    except Exception as exc:
        print(f"[FAIL] Failed to load config: {exc}")
        return 1

    if not config.programs:
        print("[FAIL] No target programs configured.")
        return 1

    test_prog = config.programs[0]
    print(f"\nTesting YouTube API query for: '{test_prog.program_name}'")
    print(f"Channel ID:  {test_prog.channel_id}")
    print(f"Playlist ID: {test_prog.playlist_id or 'None'}")

    try:
        client = YouTubeClient(api_key=api_key)
        discovery = VideoDiscovery(client)
        videos = discovery.discover_videos_for_program(test_prog, limit_videos=1)
        
        print(f"[OK] Discovered {len(videos)} video(s):")
        for v in videos:
            print(f"  - Title:        {v.get('title')}")
            print(f"    Video ID:     {v.get('video_id')}")
            print(f"    Published At: {v.get('published_at')}")

        print("\n" + "=" * 72)
        print("SMOKE TEST SUCCESSFUL — YouTube extraction is fully operational.")
        print("=" * 72)
        return 0

    except Exception as exc:
        print(f"\n[FAIL] YouTube API request failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
