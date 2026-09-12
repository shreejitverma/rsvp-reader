"""Autoplay pacing: a linear ramp from a slow start to the configured maximum WPM.

Everything is a pure function of elapsed milliseconds so it can be tested without Tk.
"""

from __future__ import annotations

from dataclasses import dataclass

MS_PER_MINUTE = 60_000


@dataclass(frozen=True, slots=True)
class Ramp:
    max_wpm: int
    duration_ms: int = 5000  # time to reach max_wpm
    start_divisor: float = 6.0  # starting speed = max_wpm / start_divisor
    min_start_wpm: int = 60  # never start slower than this

    @property
    def start_wpm(self) -> float:
        start = max(float(self.min_start_wpm), self.max_wpm / self.start_divisor)
        return min(start, float(self.max_wpm))

    def wpm_at(self, elapsed_ms: float) -> float:
        progress = min(1.0, max(0.0, elapsed_ms / self.duration_ms)) if self.duration_ms else 1.0
        return self.start_wpm + (self.max_wpm - self.start_wpm) * progress


class Autoplay:
    """Decides when the next unit is due, given an external millisecond clock.

    A unit with N words is shown for N times the single-word interval, so the configured
    WPM is a true words-per-minute figure in every display mode.
    """

    def __init__(self, ramp: Ramp, now_ms: float) -> None:
        self.ramp = ramp
        self.started_at = now_ms
        self.last_advance = now_ms

    def wpm(self, now_ms: float) -> float:
        return self.ramp.wpm_at(now_ms - self.started_at)

    def interval_ms(self, now_ms: float, words: int = 1) -> float:
        return max(1, words) * MS_PER_MINUTE / max(1.0, self.wpm(now_ms))

    def due(self, now_ms: float, words: int = 1) -> bool:
        return now_ms - self.last_advance >= self.interval_ms(now_ms, words)

    def mark_advanced(self, now_ms: float) -> None:
        self.last_advance = now_ms
