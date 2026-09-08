"""Filesystem locations: user config directory and book root defaults."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "rsvp-reader"
CONFIG_DIR_ENV = "RSVP_READER_CONFIG_DIR"
BOOK_ROOT_ENV = "RSVP_READER_BOOK_ROOT"
DEFAULT_BOOK_DIRNAME = "book"
SETTINGS_FILENAME = "settings.json"
PROGRESS_FILENAME = "progress.json"
# Settings file written by the pre-package single-script version, next to the CWD.
LEGACY_SETTINGS_FILENAME = "rsvp_settings.json"


def user_config_dir(env: dict[str, str] | None = None, platform: str = sys.platform) -> Path:
    """Per-platform config directory, overridable with RSVP_READER_CONFIG_DIR."""
    env = os.environ if env is None else env
    override = env.get(CONFIG_DIR_ENV)
    if override:
        return Path(override).expanduser()
    home = Path(env.get("HOME") or Path.home())
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    if platform.startswith("win"):
        base = env.get("APPDATA")
        return (Path(base) if base else home / "AppData" / "Roaming") / APP_NAME
    xdg = env.get("XDG_CONFIG_HOME")
    return (Path(xdg) if xdg else home / ".config") / APP_NAME


def default_book_root(env: dict[str, str] | None = None, cwd: Path | None = None) -> Path:
    env = os.environ if env is None else env
    override = env.get(BOOK_ROOT_ENV)
    if override:
        return Path(override).expanduser()
    return (cwd or Path.cwd()) / DEFAULT_BOOK_DIRNAME
