"""Pivot word and pivot letter selection for the center-anchored display.

Within a chunk exactly one word is the pivot word:
- 3 words: the middle word.
- 2 words: whichever has more letters (tie: the first).
- 1 word: that word.
Within the pivot word exactly one letter is the pivot letter, counting alphabetic
characters only: the middle for an odd count, the one just left of center for an even
count ("Bull" -> "u"). A word with no letters (a year, a price) falls back to its
digits so numbers still get a pivot box; only a word with neither has no pivot.
"""

from __future__ import annotations

from typing import NamedTuple


class PivotSplit(NamedTuple):
    """`before + letter + after` reconstructs the chunk; `letter` is None if no pivot exists."""

    before: str
    letter: str | None
    after: str


def _letter_count(word: str) -> int:
    return sum(1 for c in word if c.isalpha())


def pivot_word_index(words: list[str]) -> int:
    if len(words) <= 1:
        return 0
    if len(words) == 2:
        return 0 if _letter_count(words[0]) >= _letter_count(words[1]) else 1
    return len(words) // 2


def pivot_letter_index(word: str) -> int | None:
    positions = [i for i, c in enumerate(word) if c.isalpha()]
    if not positions:
        positions = [i for i, c in enumerate(word) if c.isdigit()]
    if not positions:
        return None
    n = len(positions)
    middle = n // 2 if n % 2 == 1 else n // 2 - 1
    return positions[middle]


def split_for_pivot(chunk: str) -> PivotSplit:
    words = chunk.split(" ")
    word_idx = pivot_word_index(words)
    pivot_word = words[word_idx]
    letter_idx = pivot_letter_index(pivot_word)
    if letter_idx is None:
        return PivotSplit(chunk, None, "")

    before = " ".join(words[:word_idx])
    if before:
        before += " "
    before += pivot_word[:letter_idx]

    after = pivot_word[letter_idx + 1 :]
    if word_idx + 1 < len(words):
        after += " " + " ".join(words[word_idx + 1 :])
    return PivotSplit(before, pivot_word[letter_idx], after)
