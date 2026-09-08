from pathlib import Path

from rsvp_reader.library import display_path, list_entries


def test_list_entries_orders_folders_then_books(tmp_path: Path):
    (tmp_path / "zeta").mkdir()
    (tmp_path / "Alpha").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "A.TXT").write_text("a")
    (tmp_path / "notes.md").write_text("m")
    (tmp_path / ".secret.txt").write_text("s")
    entries = list_entries(tmp_path)
    assert [(e.name, e.is_folder) for e in entries] == [
        ("Alpha", True),
        ("zeta", True),
        ("A.TXT", False),
        ("b.txt", False),
    ]


def test_list_entries_missing_folder(tmp_path: Path):
    assert list_entries(tmp_path / "nope") == []


def test_display_path(tmp_path: Path):
    root = tmp_path / "book"
    (root / "self help").mkdir(parents=True)
    assert display_path(root, root) == "book"
    assert display_path(root / "self help", root) == "book/self help"
    assert display_path(tmp_path, root) == str(tmp_path)
