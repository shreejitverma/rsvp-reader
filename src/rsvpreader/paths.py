"""Filesystem locations: user config directory and book root defaults."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "rsvpreader"
# Config directory name used by the 1.0.x releases, which shipped as "rsvp-reader".
LEGACY_APP_NAME = "rsvp-reader"
CONFIG_DIR_ENV = "RSVPREADER_CONFIG_DIR"
BOOK_ROOT_ENV = "RSVPREADER_BOOK_ROOT"
DEFAULT_BOOK_DIRNAME = "book"
SETTINGS_FILENAME = "settings.json"
PROGRESS_FILENAME = "progress.json"
# Settings file written by the pre-package single-script version, next to the CWD.
LEGACY_SETTINGS_FILENAME = "rsvp_settings.json"


def _platform_config_dir(env: dict[str, str], platform: str, app_name: str) -> Path:
    home = Path(env.get("HOME") or Path.home())
    if platform == "darwin":
        return home / "Library" / "Application Support" / app_name
    if platform.startswith("win"):
        base = env.get("APPDATA")
        return (Path(base) if base else home / "AppData" / "Roaming") / app_name
    xdg = env.get("XDG_CONFIG_HOME")
    return (Path(xdg) if xdg else home / ".config") / app_name


def user_config_dir(env: dict[str, str] | None = None, platform: str = sys.platform) -> Path:
    """Per-platform config directory, overridable with RSVPREADER_CONFIG_DIR."""
    env = os.environ if env is None else env
    override = env.get(CONFIG_DIR_ENV)
    if override:
        return Path(override).expanduser()
    return _platform_config_dir(env, platform, APP_NAME)


def legacy_config_dir(env: dict[str, str] | None = None, platform: str = sys.platform) -> Path:
    """Where the 1.0.x releases kept settings.json and progress.json; read on first run only."""
    env = os.environ if env is None else env
    return _platform_config_dir(env, platform, LEGACY_APP_NAME)


def default_book_root(env: dict[str, str] | None = None, cwd: Path | None = None) -> Path:
    env = os.environ if env is None else env
    override = env.get(BOOK_ROOT_ENV)
    if override:
        return Path(override).expanduser()
    return (cwd or Path.cwd()) / DEFAULT_BOOK_DIRNAME
