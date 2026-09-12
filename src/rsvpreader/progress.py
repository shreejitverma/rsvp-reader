"""Per-book reading position, keyed by the book's absolute path."""

from __future__ import annotations

from pathlib import Path

from rsvpreader.storage import read_json, write_json_atomic


def _key(book_path: Path) -> str:
    return str(Path(book_path).expanduser().resolve())


class ProgressStore:
    """Maps book path -> character offset into the joined unit text (see ReadingSession).

    Reads from the first existing `legacy_paths` entry when `path` does not exist yet, so a
    rename of the config directory keeps every reading position; saves always go to `path`.
    """

    def __init__(self, path: Path, legacy_paths: tuple[Path, ...] = ()) -> None:
        self.path = path
        self.legacy_paths = legacy_paths
        self._offsets: dict[str, int] | None = None

    def _read(self) -> dict[str, object]:
        data = read_json(self.path)
        if data is None:
            for legacy in self.legacy_paths:
                data = read_json(legacy)
                if data is not None:
                    break
        return data or {}

    def _load(self) -> dict[str, int]:
        if self._offsets is None:
            data = self._read()
            self._offsets = {k: int(v) for k, v in data.items() if isinstance(v, int) and v >= 0}
        return self._offsets

    def get(self, book_path: Path) -> int:
        return self._load().get(_key(book_path), 0)

    def set(self, book_path: Path, offset: int) -> None:
        self._load()[_key(book_path)] = max(0, int(offset))

    def save(self) -> bool:
        if self._offsets is None:
            return True
        try:
            write_json_atomic(self.path, dict(self._offsets))
        except OSError:
            return False
        return True
