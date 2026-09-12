"""Text normalization, tokenization and reading-unit construction.

Pure functions only; `load_book_text` is the single I/O entry point.

Chunking rules (word-chunk mode):
1. Regular punctuation (comma, semicolon, colon, apostrophe, dashes) attaches to its
   word and never forces a break; the chunk keeps filling toward `chunk_size`.
2. A sentence terminator (. ! ?) forces the chunk to close on the word carrying it.
3. An opening double quote (straight or curly) forces the previous chunk to close, so
   the quoted word always starts a new chunk.
4. A closing double quote forces the chunk to close on the word carrying it.

Sentence mode: a unit runs up to and including the next terminator (optionally
followed by closing quotes), or to the end of the text.

Normalization repairs text that was pasted without spaces around punctuation
(`forth,The`, `it."Believe`, `end.Next`) while leaving decimals (`0.99365`),
thousands separators (`1,000`) and lowercase abbreviations (`e.g.`, `7.25p.m.`) intact.
Straight double quotes are classified by parity: odd occurrences open, even close.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

STRAIGHT_QUOTE = '"'
OPEN_CURLY = "“"
CLOSE_CURLY = "”"
OPENING_QUOTES = frozenset((STRAIGHT_QUOTE, OPEN_CURLY))
CLOSING_QUOTES = frozenset((STRAIGHT_QUOTE, CLOSE_CURLY))
SENTENCE_TERMINATORS = frozenset(".!?")

# Characters that may trail a word without affecting whether it ends a unit.
_TRAILING_IGNORED = " -–—)]}"
# Characters that legitimately follow a closing quote with no space.
_NO_SPACE_AFTER_CLOSE = frozenset(" .,;:!?)]}" + CLOSE_CURLY + STRAIGHT_QUOTE + "'’")
# A standalone token made only of these glues to the previous word without a space.
_GLUE_TIGHT = frozenset(".,;:!?" + STRAIGHT_QUOTE + CLOSE_CURLY + "'’")

_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Word:
    """One display word. `opens_quote` marks a word that begins with a double quote."""

    text: str
    opens_quote: bool = False


def _is_glued_sentence_break(prev: str, nxt: str) -> bool:
    """`end.Next` / `wait...Then` are sentence breaks; `U.S.A.`, `e.g.`, `3.14` are not."""
    return nxt.isupper() and (prev.islower() or prev == ".")


def normalize_text(raw: str) -> str:
    """Collapse whitespace and insert the spaces that glued punctuation is missing."""
    text = _WS_RE.sub(" ", raw).strip()
    out: list[str] = []
    quote_open = False
    n = len(text)
    for i, ch in enumerate(text):
        prev = out[-1] if out else ""
        nxt = text[i + 1] if i + 1 < n else ""
        if ch == STRAIGHT_QUOTE:
            closing = quote_open
            quote_open = not quote_open
        elif ch == OPEN_CURLY:
            closing = False
        elif ch == CLOSE_CURLY:
            closing = True
        else:
            out.append(ch)
            glued_break = ch in SENTENCE_TERMINATORS and _is_glued_sentence_break(prev, nxt)
            if glued_break or (ch == "," and nxt.isalpha()):
                out.append(" ")
            continue
        if closing:
            if prev == " ":
                out.pop()
            out.append(ch)
            if nxt and nxt not in _NO_SPACE_AFTER_CLOSE:
                out.append(" ")
        else:
            if prev and prev != " ":
                out.append(" ")
            out.append(ch)
    return _WS_RE.sub(" ", "".join(out)).strip()


def _has_alnum(token: str) -> bool:
    return any(c.isalnum() for c in token)


def tokenize(text: str) -> list[Word]:
    """Split normalized text into words.

    A lone opening quote is glued onto the following word. A token with no letters or
    digits (a spaced dash, a stray period) is glued onto the previous word so it never
    occupies a chunk slot of its own.
    """
    words: list[Word] = []
    pending_quote = ""
    for raw_tok in text.split():
        tok = pending_quote + raw_tok
        pending_quote = ""
        if tok in OPENING_QUOTES:
            pending_quote = tok
            continue
        if not _has_alnum(tok) and words and tok[0] not in OPENING_QUOTES:
            last = words[-1]
            sep = "" if tok[0] in _GLUE_TIGHT else " "
            words[-1] = Word(last.text + sep + tok, last.opens_quote)
            continue
        words.append(Word(tok, opens_quote=tok[0] in OPENING_QUOTES))
    return words


def _core(word: str) -> str:
    return word.rstrip(_TRAILING_IGNORED)


def ends_chunk(word: str) -> bool:
    """True if the word carries a sentence terminator or a closing double quote."""
    core = _core(word)
    return bool(core) and (core[-1] in SENTENCE_TERMINATORS or core[-1] in CLOSING_QUOTES)


def ends_sentence(word: str) -> bool:
    """True if the word carries a sentence terminator, optionally inside closing quotes."""
    core = _core(word).rstrip(STRAIGHT_QUOTE + CLOSE_CURLY + "'’")
    return bool(core) and core[-1] in SENTENCE_TERMINATORS


def build_chunks(text: str, chunk_size: int) -> list[str]:
    """Group words into chunks of at most `chunk_size`, honoring the chunking rules."""
    if chunk_size < 1:
        raise ValueError(f"chunk_size must be >= 1, got {chunk_size}")
    chunks: list[str] = []
    current: list[str] = []
    for word in tokenize(text):
        if word.opens_quote and current:
            chunks.append(" ".join(current))
            current = []
        current.append(word.text)
        if ends_chunk(word.text) or len(current) >= chunk_size:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def build_sentences(text: str) -> list[str]:
    """Group words into sentences ending at a terminator (or the end of the text)."""
    sentences: list[str] = []
    current: list[str] = []
    for word in tokenize(text):
        current.append(word.text)
        if ends_sentence(word.text):
            sentences.append(" ".join(current))
            current = []
    if current:
        sentences.append(" ".join(current))
    return sentences


def build_units(text: str, *, sentence_mode: bool, chunk_size: int) -> list[str]:
    """Dispatch to sentence or chunk building based on the reading mode."""
    if sentence_mode:
        return build_sentences(text)
    return build_chunks(text, chunk_size)


def word_count(unit: str) -> int:
    """Number of display words in a unit; drives how long autoplay shows it."""
    return max(1, len(unit.split()))


def decode_text(data: bytes) -> str:
    """Decode a book file: UTF-8 (BOM tolerant) first, then Windows-1252, never raising."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def load_book_text(path: str | Path) -> str:
    """Read and normalize a book file."""
    return normalize_text(decode_text(Path(path).read_bytes()))
