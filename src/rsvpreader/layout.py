"""Geometry for the center-anchored pivot display (pure; no Tk).

The pivot letter sits in a fixed-size box whose center is pinned to the screen center.
Text before the pivot is laid out right-to-left from the box's left edge, text after it
left-to-right from the right edge, so the pivot letter never moves between chunks.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

Measure = Callable[[str], int]


@dataclass(frozen=True, slots=True)
class PivotBox:
    left: float
    right: float
    top: float
    bottom: float
    center_x: float
    center_y: float
    tick_top: tuple[float, float, float, float]
    tick_bottom: tuple[float, float, float, float]

    @property
    def text_top(self) -> float:
        """y of the text line's top edge, so glyphs align with the box vertically."""
        return self.top + PAD_Y


PAD_X = 2
PAD_Y = 2
TICK_GAP = 4
TICK_LENGTH = 14


def pivot_box(*, center_x: float, center_y: float, text_height: int, inner_width: int) -> PivotBox:
    """Box edges are whole pixels: Tk snaps canvas text to integer x, so a half-pixel edge
    would leave the flush text one pixel off. An odd inner size rounds the box up by 1 px."""
    half_w = (inner_width + 1) // 2 + PAD_X
    half_h = (text_height + 1) // 2 + PAD_Y
    top = center_y - half_h
    bottom = center_y + half_h
    return PivotBox(
        left=center_x - half_w,
        right=center_x + half_w,
        top=top,
        bottom=bottom,
        center_x=center_x,
        center_y=center_y,
        tick_top=(center_x, top - TICK_GAP, center_x, top - TICK_GAP - TICK_LENGTH),
        tick_bottom=(center_x, bottom + TICK_GAP, center_x, bottom + TICK_GAP + TICK_LENGTH),
    )


def flow_positions(
    words: list[str], measure: Measure, space_width: int, edge_x: float, anchor_right: bool
) -> list[tuple[float, str]]:
    """x positions (left edges) for `words` laid out flush against `edge_x`.

    With `anchor_right` the run ends exactly at `edge_x`; otherwise it starts there.
    """
    if not words:
        return []
    widths = [measure(w) for w in words]
    total = sum(widths) + space_width * (len(words) - 1)
    cursor = edge_x - total if anchor_right else edge_x
    positions: list[tuple[float, str]] = []
    for word, width in zip(words, widths, strict=True):
        positions.append((cursor, word))
        cursor += width + space_width
    return positions
