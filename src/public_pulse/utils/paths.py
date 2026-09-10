"""Repository-relative path resolution, with environment variable overrides.

Configs (configs/layer1.yaml etc.) store checkpoint/label_map paths
relative to the repository root (e.g. "models/layer1_utility/label_map.json").
This module resolves those to absolute paths, and lets each be overridden
by an environment variable without touching any config file -- this is
the "configuration-driven, not hard-coded" mechanism Phase 4 requires for
checkpoint paths (e.g. so a deployment can point at a real checkpoint
location without a code change).
"""

import os
from pathlib import Path

# src/public_pulse/utils/paths.py -> parents[3] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]


def resolve_repo_path(relative_or_absolute_path: str, env_override_var: str = None) -> Path:
    """Resolve a config-declared path to an absolute filesystem path.

    If `env_override_var` is set in the environment, its value wins
    entirely (also resolved relative to REPO_ROOT if it isn't already
    absolute) -- this is the override mechanism for deployments where the
    checkpoint lives somewhere other than the path baked into the yaml
    config (e.g. a mounted volume, a downloaded Hugging Face Hub cache).
    """
    if env_override_var:
        override = os.environ.get(env_override_var)
        if override:
            path = Path(override)
            return path if path.is_absolute() else (REPO_ROOT / path)

    path = Path(relative_or_absolute_path)
    return path if path.is_absolute() else (REPO_ROOT / path)
