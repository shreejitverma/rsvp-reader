"""User settings: a validated dataclass plus a JSON-backed store."""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any

from rsvpreader.colors import FALLBACK_COLOR, normalize_hex
from rsvpreader.storage import read_json, write_json_atomic

CHUNK_SIZES = (1, 2, 3)
WPM_RANGE = (60, 1200)
FONT_SIZE_RANGE = (16, 100)
BRIGHTNESS_RANGE = (10, 100)


def platform_default_font_family(platform: str = sys.platform) -> str:
    if platform == "darwin":
        return "Menlo"
    if platform.startswith("win"):
        return "Consolas"
    return "DejaVu Sans Mono"


def _clamp(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, number))


@dataclass(frozen=True, slots=True)
class Settings:
    chunk_size: int = 3
    wpm: int = 300  # maximum speed autoplay ramps up to
    font_family: str = ""  # empty means "platform default"
    font_size: int = 40
    brightness: int = 100
    font_color: str = FALLBACK_COLOR
    sentence_mode: bool = False

    def sanitized(self) -> Settings:
        """Return a copy with every field coerced into its valid range."""
        defaults = Settings()
        chunk = _clamp(self.chunk_size, CHUNK_SIZES[0], CHUNK_SIZES[-1], defaults.chunk_size)
        family = self.font_family if isinstance(self.font_family, str) else ""
        return Settings(
            chunk_size=chunk,
            wpm=_clamp(self.wpm, *WPM_RANGE, defaults.wpm),
            font_family=family.strip(),
            font_size=_clamp(self.font_size, *FONT_SIZE_RANGE, defaults.font_size),
            brightness=_clamp(self.brightness, *BRIGHTNESS_RANGE, defaults.brightness),
            font_color=normalize_hex(self.font_color),
            sentence_mode=bool(self.sentence_mode),
        )

    def with_changes(self, **changes: Any) -> Settings:
        return replace(self, **changes).sanitized()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Settings:
        """Build from a possibly partial or corrupt mapping; unknown keys are ignored."""
        known = {f.name for f in fields(cls)}
        picked = {k: v for k, v in (data or {}).items() if k in known}
        return cls(**picked).sanitized()


class SettingsStore:
    """Loads and saves `Settings` at `path`, migrating from `legacy_paths` on first run."""

    def __init__(self, path: Path, legacy_paths: tuple[Path, ...] = ()) -> None:
        self.path = path
        self.legacy_paths = legacy_paths

    def load(self) -> Settings:
        data = read_json(self.path)
        if data is None:
            for legacy in self.legacy_paths:
                data = read_json(legacy)
                if data is not None:
                    break
        return Settings.from_dict(data)

    def save(self, settings: Settings) -> bool:
        """Persist settings; returns False (without raising) if the write fails."""
        try:
            write_json_atomic(self.path, settings.sanitized().to_dict())
        except OSError:
            return False
        return True
