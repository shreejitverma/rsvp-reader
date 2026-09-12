"""Reading position over a list of display units (chunks or sentences)."""

from __future__ import annotations

from rsvpreader.text import build_units


class ReadingSession:
    """Holds the normalized text, the current units and the cursor into them.

    Positions persist as a character offset into `" ".join(units)`. Because chunk and
    sentence mode tokenize identically, that joined string is the same in both modes,
    so an offset survives a mode or chunk-size change.
    """

    def __init__(self, text: str, *, sentence_mode: bool, chunk_size: int) -> None:
        self.text = text
        self.sentence_mode = sentence_mode
        self.chunk_size = chunk_size
        self.units: list[str] = build_units(
            text, sentence_mode=sentence_mode, chunk_size=chunk_size
        )
        self.index = 0

    @property
    def count(self) -> int:
        return len(self.units)

    @property
    def current(self) -> str:
        return self.units[self.index] if self.units else ""

    @property
    def at_end(self) -> bool:
        return self.index >= self.count - 1

    @property
    def at_start(self) -> bool:
        return self.index <= 0

    @property
    def progress(self) -> float:
        """Fraction of units shown so far, 0.0 for an empty book."""
        return (self.index + 1) / self.count if self.units else 0.0

    def advance(self) -> bool:
        if self.at_end:
            return False
        self.index += 1
        return True

    def back(self) -> bool:
        if self.at_start:
            return False
        self.index -= 1
        return True

    def first(self) -> None:
        self.index = 0

    def last(self) -> None:
        self.index = max(0, self.count - 1)

    @property
    def char_offset(self) -> int:
        return sum(len(u) + 1 for u in self.units[: self.index])

    def seek_offset(self, offset: int) -> None:
        """Move to the unit that contains `offset` (never skipping past unread words)."""
        running = 0
        target = 0
        for i, unit in enumerate(self.units):
            if running > offset:
                break
            target = i
            running += len(unit) + 1
        self.index = target

    def rebuild(self, *, sentence_mode: bool, chunk_size: int) -> None:
        """Re-derive units for new display settings, preserving the reading position."""
        offset = self.char_offset
        self.sentence_mode = sentence_mode
        self.chunk_size = chunk_size
        self.units = build_units(self.text, sentence_mode=sentence_mode, chunk_size=chunk_size)
        self.seek_offset(offset)
