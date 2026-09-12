"""Colors, font resolution and font roles for the Tk views."""

from __future__ import annotations

from collections.abc import Iterable

BG = "#000000"
PIVOT_FG = "#FFFFFF"
PANEL_BG = "#111111"
PANEL_FG = "#FFFFFF"
PANEL_TROUGH = "#333333"
STATUS_BRIGHTNESS_FACTOR = 0.45  # status/hint text is the accent color, dimmed

UI_FONT_CANDIDATES = ("Menlo", "Consolas", "DejaVu Sans Mono", "Courier New", "Courier")
READER_FONT_CHOICES = (
    "Menlo",
    "Consolas",
    "DejaVu Sans Mono",
    "Courier New",
    "Monaco",
    "Georgia",
    "Times New Roman",
    "Arial",
    "Helvetica",
    "Verdana",
)


def resolve_font_family(requested: str, installed: Iterable[str], candidates: Iterable[str]) -> str:
    """`requested` if installed, else the first installed candidate, else `requested`/Courier."""
    installed_set = set(installed)
    if requested and requested in installed_set:
        return requested
    for family in candidates:
        if family in installed_set:
            return family
    return requested or "Courier"


def available_reader_fonts(installed: Iterable[str], current: str) -> list[str]:
    """Installed choices from READER_FONT_CHOICES, always including the current family."""
    installed_set = set(installed)
    choices = [f for f in READER_FONT_CHOICES if f in installed_set]
    if current and current not in choices:
        choices.insert(0, current)
    return choices or [current]


class Theme:
    """Font tuples for every non-reader text role, built on one resolved UI family."""

    def __init__(self, ui_family: str) -> None:
        self.ui_family = ui_family
        self.browser = (ui_family, 20)
        self.header = (ui_family, 14, "bold")
        self.status = (ui_family, 11)
        self.hint = (ui_family, 11)
        self.gear = (ui_family, 22)
        self.panel_label = (ui_family, 13, "bold")
        self.panel = (ui_family, 12)
