"""Color helpers (pure)."""

from __future__ import annotations

import re

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
FALLBACK_COLOR = "#FF4500"


def normalize_hex(color: str, fallback: str = FALLBACK_COLOR) -> str:
    """Return `#RRGGBB` uppercase, or `fallback` if the input is not a 6-digit hex color."""
    match = _HEX_RE.match(color.strip()) if isinstance(color, str) else None
    if not match:
        return fallback
    return "#" + match.group(1).upper()


def apply_brightness(color: str, brightness_pct: int | float) -> str:
    """Scale each channel of `#RRGGBB` by `brightness_pct` (0-100)."""
    hex_color = normalize_hex(color)[1:]
    scale = max(0.0, min(100.0, float(brightness_pct))) / 100.0
    channels = (round(int(hex_color[i : i + 2], 16) * scale) for i in (0, 2, 4))
    return "#" + "".join(f"{max(0, min(255, c)):02X}" for c in channels)
