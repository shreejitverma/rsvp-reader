"""End-to-end smoke tests against a real Tk window. Skipped when no display is available."""

from __future__ import annotations

import contextlib
from pathlib import Path

import pytest

tk = pytest.importorskip("tkinter")

from rsvpreader.app import App  # noqa: E402
from rsvpreader.browser_view import FolderView  # noqa: E402
from rsvpreader.progress import ProgressStore  # noqa: E402
from rsvpreader.reader_view import ReaderView  # noqa: E402
from rsvpreader.settings import Settings, SettingsStore  # noqa: E402

BOOK = 'One two three four. "Five six," seven eight nine. Ten eleven twelve.'


class Key:
    def __init__(self, keysym: str, char: str = "") -> None:
        self.keysym = keysym
        self.char = char


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - headless CI
        pytest.skip(f"no display: {exc}")
    yield window
    with contextlib.suppress(tk.TclError):
        window.destroy()


@pytest.fixture
def library(tmp_path: Path) -> Path:
    book_root = tmp_path / "book"
    (book_root / "fiction").mkdir(parents=True)
    (book_root / "alpha.txt").write_text(BOOK, encoding="utf-8")
    (book_root / "fiction" / "novel.txt").write_text("A b c. D e f.", encoding="utf-8")
    return book_root


def make_app(root, tmp_path: Path, library: Path, settings: Settings | None = None) -> App:
    store = SettingsStore(tmp_path / "cfg" / "settings.json")
    if settings is not None:
        store.save(settings)
    app = App(
        root,
        book_root=library,
        settings_store=store,
        progress_store=ProgressStore(tmp_path / "cfg" / "progress.json"),
        fullscreen=False,
    )
    root.update()
    return app


def test_browser_lists_and_opens(root, tmp_path, library):
    app = make_app(root, tmp_path, library)
    view = app.view
    assert isinstance(view, FolderView)
    assert [e.name for e in view.entries] == ["fiction", "alpha.txt"]
    assert view.header.cget("text") == "book"

    view.on_key(Key("Down"))
    view.on_key(Key("Return"))
    root.update()
    assert isinstance(app.view, ReaderView)
    assert app.view.session.current == "One two three"
    assert "Chunk 1 / 5" in app.view.status.cget("text")

    app.on_escape()
    root.update()
    assert isinstance(app.view, FolderView)
    app.view.on_key(Key("Up"))
    app.view.on_key(Key("Return"))
    root.update()
    assert app.view.header.cget("text") == "book/fiction"
    app.on_escape()
    assert app.view.header.cget("text") == "book"


def test_reader_navigation_settings_and_resume(root, tmp_path, library):
    app = make_app(root, tmp_path, library, Settings(chunk_size=3, wpm=300))
    app.open_book(library / "alpha.txt")
    root.update()
    reader = app.view
    assert isinstance(reader, ReaderView)
    assert reader.session.units == [
        "One two three",
        "four.",
        '"Five six,"',
        "seven eight nine.",
        "Ten eleven twelve.",
    ]

    reader.on_key(Key("Right"))
    reader.on_key(Key("space"))
    assert reader.session.index == 2
    reader.on_key(Key("Left"))
    assert reader.session.index == 1
    reader.on_key(Key("Up"))
    assert app.settings.wpm == 310
    reader.on_key(Key("End"))
    assert reader.session.at_end
    reader.on_key(Key("Home"))
    assert reader.session.index == 0

    # Real Tk events on the canvas: click advances, secondary click goes back.
    root.event_generate("<ButtonPress-1>", x=10, y=10)
    reader.canvas.event_generate("<ButtonPress-1>", x=10, y=10)
    reader.canvas.event_generate("<ButtonRelease-1>", x=10, y=10)
    root.update()
    assert reader.session.index == 1
    reader.canvas.event_generate("<ButtonPress-2>", x=10, y=10)
    reader.canvas.event_generate("<ButtonRelease-2>", x=10, y=10)
    root.update()
    assert reader.session.index == 0

    # Switching modes keeps the reading position and redraws without error.
    reader.on_key(Key("Right"))  # "four."
    app.update_settings(sentence_mode=True)
    root.update()
    assert reader.session.current == "One two three four."
    app.update_settings(sentence_mode=False, chunk_size=1)
    root.update()
    assert reader.session.current == "One"

    # Settings panel opens, reflects state, and closes on Escape.
    app.toggle_settings_panel()
    root.update()
    assert app.settings_panel is not None
    assert app.settings_panel.chunk_var.get() == 1
    app.on_escape()
    assert app.settings_panel is None

    # Leaving the reader persists the position; reopening resumes there.
    reader.on_key(Key("Right"))
    reader.on_key(Key("Right"))
    assert reader.session.current == "three"
    app.on_escape()
    root.update()
    assert ProgressStore(tmp_path / "cfg" / "progress.json").get(library / "alpha.txt") > 0
    app.open_book(library / "alpha.txt")
    root.update()
    assert app.view.session.current == "three"

    # Draw items exist on the canvas: ticks, box, pivot letter, flow text.
    kinds = {app.view.canvas.type(i) for i in app.view.canvas.find_all()}
    assert {"line", "rectangle", "text"} <= kinds

    app.quit()
    assert SettingsStore(tmp_path / "cfg" / "settings.json").load().chunk_size == 1


def test_autoplay_advances_and_stops_at_end(root, tmp_path, library):
    app = make_app(root, tmp_path, library, Settings(chunk_size=1, wpm=1200))
    app.open_book(library / "fiction" / "novel.txt")
    root.update()
    reader = app.view
    reader.toggle_autoplay()
    assert reader.autoplay_active
    deadline = root.after(4000, root.quit)
    while reader.autoplay_active:
        root.update()
        if not reader.autoplay_active:
            break
        root.after(20)
        root.update_idletasks()
    root.after_cancel(deadline)
    assert reader.session.at_end
    assert not reader.autoplay_active


def test_unreadable_and_empty_files(root, tmp_path, library):
    (library / "empty.txt").write_text("", encoding="utf-8")
    (library / "latin.txt").write_bytes(b"caf\xe9 au lait. Fin.")
    app = make_app(root, tmp_path, library)
    app.open_book(library / "empty.txt")
    root.update()
    assert app.view.session.count == 0
    assert "Chunk 1 / 0" in app.view.status.cget("text")
    app.view.on_key(Key("Right"))  # must not raise
    app.on_escape()
    app.open_book(library / "latin.txt")
    root.update()
    assert app.view.session.current == "café au lait."


def test_pivot_letter_is_pinned_and_text_is_flush(root, tmp_path, library):
    """Rendered bounding boxes: the pivot letter never moves, and the flow text hugs the box."""
    app = make_app(root, tmp_path, library, Settings(chunk_size=3, font_size=40))
    app.open_book(library / "alpha.txt")
    root.update()
    reader = app.view
    canvas = reader.canvas
    center_x = canvas.winfo_width() // 2
    center_y = canvas.winfo_height() // 2

    def items(kind):
        return [i for i in canvas.find_all() if canvas.type(i) == kind]

    letter_centers = []
    for _ in range(reader.session.count):
        rect = items("rectangle")
        assert len(rect) == 1, reader.session.current
        box_l, box_t, box_r, box_b = canvas.coords(rect[0])
        assert abs((box_l + box_r) / 2 - center_x) < 0.01
        assert abs((box_t + box_b) / 2 - center_y) < 0.01

        texts = items("text")
        letter = next(i for i in texts if canvas.itemcget(i, "fill") == "#FFFFFF")
        lx1, ly1, lx2, ly2 = canvas.bbox(letter)
        letter_centers.append(((lx1 + lx2) / 2, (ly1 + ly2) / 2))
        assert box_l <= lx1 and lx2 <= box_r, "pivot letter overflows its box"

        words = [i for i in texts if i != letter]
        before = [canvas.bbox(i) for i in words if canvas.bbox(i)[2] <= box_l + 1]
        after = [canvas.bbox(i) for i in words if canvas.bbox(i)[0] >= box_r - 1]
        assert len(before) + len(after) == len(words), "a word overlaps the pivot box"
        if before:
            assert max(b[2] for b in before) >= box_l - 3, "gap between text and box"
        if after:
            assert min(a[0] for a in after) <= box_r + 3, "gap between box and text"
        tops = {canvas.bbox(i)[1] for i in words}
        assert len(tops) <= 1, "flow words do not share a baseline"
        if not reader.step(True):
            break

    xs = {round(x) for x, _ in letter_centers}
    ys = {round(y) for _, y in letter_centers}
    assert len(xs) <= 2 and len(ys) <= 2, f"pivot letter drifted: {letter_centers}"
    assert len(letter_centers) == reader.session.count
