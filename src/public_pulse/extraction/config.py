"""Configuration loader for YouTube extraction system (Phase 6).

Loads target program definitions from configs/programs.yaml and API credentials
from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml

from public_pulse.extraction.exceptions import ConfigurationError

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROGRAMS_YAML = REPO_ROOT / "configs" / "programs.yaml"


@dataclass
class ProgramConfig:
    """Configuration for a single target program."""

    program_name: str
    channel_id: str
    playlist_id: Optional[str] = None
    program_type: Optional[str] = None
    keywords: List[str] = field(default_factory=list)


@dataclass
class ExtractionConfig:
    """Global configuration for extraction service run."""

    api_key: str
    programs: List[ProgramConfig] = field(default_factory=list)
    limit_videos: Optional[int] = None
    limit_comments: Optional[int] = None
    since: Optional[str] = None
    until: Optional[str] = None
    dry_run: bool = False

    @classmethod
    def load(
        cls,
        programs_path: Optional[Path] = None,
        require_api_key: bool = True,
        **overrides,
    ) -> ExtractionConfig:
        """Load configuration from environment and YAML file."""
        api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
        if require_api_key and not api_key:
            raise ConfigurationError(
                "YOUTUBE_API_KEY environment variable is missing or empty. "
                "Set it in your environment or .env file before running extraction."
            )

        path = programs_path or DEFAULT_PROGRAMS_YAML
        if not path.exists():
            raise ConfigurationError(f"Program configuration file not found at: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as exc:
            raise ConfigurationError(f"Failed to parse programs configuration {path}: {exc}") from exc

        raw_programs = data.get("programs", [])
        programs = []
        for item in raw_programs:
            prog = ProgramConfig(
                program_name=item["program_name"],
                channel_id=item["channel_id"],
                playlist_id=item.get("playlist_id"),
                program_type=item.get("program_type"),
                keywords=item.get("keywords", []),
            )
            programs.append(prog)

        return cls(
            api_key=api_key,
            programs=programs,
            **overrides,
        )
