import json
from pathlib import Path

from rsvpreader.progress import ProgressStore


def test_missing_file_is_empty(tmp_path: Path):
    store = ProgressStore(tmp_path / "p.json")
    assert store.get(tmp_path / "a.txt") == 0
    assert store.save()


def test_round_trip_and_normalization(tmp_path: Path):
    store = ProgressStore(tmp_path / "p.json")
    book = tmp_path / "a.txt"
    store.set(book, 123)
    store.set(tmp_path / "b.txt", -5)
    assert store.save()
    again = ProgressStore(tmp_path / "p.json")
    assert again.get(book) == 123
    assert again.get(tmp_path / "b.txt") == 0
    assert again.get(tmp_path / "sub" / ".." / "a.txt") == 123


def test_corrupt_values_dropped(tmp_path: Path):
    p = tmp_path / "p.json"
    x, y, z = (tmp_path / name for name in ("x", "y", "z"))
    p.write_text(
        json.dumps({str(x.resolve()): "no", str(y.resolve()): -1, str(z.resolve()): 7}),
        encoding="utf-8",
    )
    store = ProgressStore(p)
    assert store.get(z) == 7
    assert store.get(x) == 0
    assert store.get(y) == 0


def test_legacy_file_is_read_until_new_file_exists(tmp_path: Path):
    book = tmp_path / "a.txt"
    legacy = tmp_path / "old" / "progress.json"
    legacy.parent.mkdir()
    legacy.write_text(json.dumps({str(book.resolve()): 42}), encoding="utf-8")
    new = tmp_path / "new" / "progress.json"

    store = ProgressStore(new, legacy_paths=(legacy,))
    assert store.get(book) == 42
    store.set(book, 43)
    assert store.save()
    assert new.exists()

    # Once the new file exists it wins, and the legacy file is left untouched.
    assert ProgressStore(new, legacy_paths=(legacy,)).get(book) == 43
    assert json.loads(legacy.read_text(encoding="utf-8")) == {str(book.resolve()): 42}
