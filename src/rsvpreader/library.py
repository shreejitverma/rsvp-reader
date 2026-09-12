"""Book folder listing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BOOK_EXTENSIONS = frozenset({".txt"})


@dataclass(frozen=True, slots=True)
class Entry:
    path: Path
    is_folder: bool

    @property
    def name(self) -> str:
        return self.path.name


def is_book(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in BOOK_EXTENSIONS


def list_entries(folder: Path) -> list[Entry]:
    """Visible subfolders first, then books, each sorted case-insensitively."""
    try:
        children = [p for p in folder.iterdir() if not p.name.startswith(".")]
    except OSError:
        return []
    key = lambda p: p.name.casefold()  # noqa: E731
    folders = sorted((p for p in children if p.is_dir()), key=key)
    books = sorted((p for p in children if is_book(p)), key=key)
    return [Entry(p, True) for p in folders] + [Entry(p, False) for p in books]


def display_path(folder: Path, root: Path) -> str:
    """`root.name` plus the relative path, e.g. `book/selfhelp`."""
    try:
        rel = folder.resolve().relative_to(root.resolve())
    except ValueError:
        return str(folder)
    return root.name if str(rel) == "." else f"{root.name}/{rel.as_posix()}"
