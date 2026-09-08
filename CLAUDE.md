# RSVP Reader

Tkinter RSVP (Spritz-style) reader packaged under `src/rsvp_reader/`; see README.md for behavior and layout.

## Commands

```sh
uv sync                                   # Python 3.12 via .python-version (has Tk; Homebrew 3.14 does not)
uv run pytest                             # 128 tests, ~2 s; Tk smoke tests open a real window and skip headless
uv run ruff check src tests && uv run ruff format --check src tests
uv run rsvp-reader --windowed             # run the app
uv run rsvp-reader --dump-chunks FILE     # inspect chunking without a GUI (works on Tk-less Pythons too)
```

Release: bump `__version__` in `src/rsvp_reader/__init__.py` (the only version source), merge, then publish a GitHub release tagged `v<version>`; `.github/workflows/publish.yml` uploads to PyPI via trusted publishing.

## Rules

- Keep `text.py`, `pivot.py`, `session.py`, `autoplay.py`, `layout.py`, `settings.py`, `progress.py`, `library.py` free of tkinter imports; they are the tested core.
- Any chunking change must be checked against real books with `--dump-chunks`; decimals, abbreviations and straight-quote parity are the known traps.
- `rsvp_reader.py` at the repo root is a launcher shim, kept so `python rsvp_reader.py` still works; do not put logic there.
- `book/` holds personal texts and is gitignored; never commit it.
- `screencapture` is blocked for this terminal; verify rendering through canvas bboxes (see `tests/test_gui_smoke.py`) rather than screenshots.
