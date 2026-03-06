"""Load app_config.toml page toggle settings."""

import os

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # Python < 3.11 fallback

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "app_config.toml"
)


def _load() -> dict:
    with open(_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def is_page_enabled(page_key: str) -> bool:
    """Check if a page is enabled. Returns True if config is missing."""
    try:
        cfg = _load()
        return cfg.get("pages", {}).get(page_key, True)
    except FileNotFoundError:
        return True
