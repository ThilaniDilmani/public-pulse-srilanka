"""Load YAML configs + .env secrets."""

import os
import yaml


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def get_env(key: str, default=None):
    return os.environ.get(key, default)
