import json
from pathlib import Path

from rsvp_reader.progress import ProgressStore


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
