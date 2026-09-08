# RSVP Reader

A Spritz-style rapid serial visual presentation reader for plain-text books.
It shows one chunk of one to three words at a time with a fixed pivot letter pinned to the center of the screen, or one full sentence at a time, and remembers where you stopped in every book.

[![CI](https://github.com/shreejitverma/rsvp-reader/actions/workflows/ci.yml/badge.svg)](https://github.com/shreejitverma/rsvp-reader/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/rsvp-reader)](https://pypi.org/project/rsvp-reader/)

## Install and run

Requires Python 3.10 or newer with Tk.
On macOS, Homebrew's Python ships without Tk; `uv` installs a Python that has it.

From PyPI:

```sh
uv tool install rsvp-reader   # or: pipx install rsvp-reader, pip install rsvp-reader
rsvp-reader                   # fullscreen, reads ./book
rsvp-reader --windowed        # normal window
rsvp-reader ~/Books           # a different book folder
```

From a checkout:

```sh
uv sync
uv run rsvp-reader --windowed
```

`python rsvp_reader.py` still works as a launcher for the old invocation.

Put `.txt` files, in any folder structure, under `book/` next to where you run the command, or point `RSVP_READER_BOOK_ROOT` or the positional argument at another folder.

## Controls

| Where | Input | Action |
|---|---|---|
| Browser | Click, Enter, Space, Right | Open folder or book |
| Browser | Up, Down | Move selection |
| Browser | Backspace, Left | Back one folder |
| Reader | Click, Right, Space | Next chunk or sentence |
| Reader | Secondary click, Left | Previous chunk or sentence |
| Reader | Hold click 2 s | Autoplay while held, ramping up to the max WPM over 5 s |
| Reader | p | Toggle autoplay (same ramp) |
| Reader | Up, Down | Max WPM plus or minus 10 |
| Reader | Home, End | First or last unit |
| Reader | Hold secondary click 3 s | Open settings |
| Anywhere | s or the gear icon | Toggle settings |
| Anywhere | Esc | Close settings, else back one level, else leave fullscreen |
| Anywhere | q | Quit |

Autoplay speed is true words per minute: a three-word chunk is shown three times as long as a single word, and a sentence for as long as its word count implies.

## Settings

Chunk size (1, 2 or 3 words), max autoplay WPM, font family and size, brightness, text color (native color picker) and sentence mode.
Changes apply live, rebuild the current book without losing your place, and persist to `settings.json` in the user config directory:

| Platform | Location |
|---|---|
| macOS | `~/Library/Application Support/rsvp-reader/` |
| Linux | `$XDG_CONFIG_HOME/rsvp-reader/` or `~/.config/rsvp-reader/` |
| Windows | `%APPDATA%\rsvp-reader\` |

Override with `--config-dir` or `RSVP_READER_CONFIG_DIR`.
A legacy `rsvp_settings.json` in the working directory is imported on first run.
Reading positions live in `progress.json` in the same directory, keyed by the book's absolute path.

## How text is chunked

1. Regular punctuation (comma, semicolon, colon, apostrophe, dashes) attaches to its word and never forces a break.
2. A sentence terminator (`.` `!` `?`) closes the chunk on the word carrying it.
3. An opening double quote (straight or curly) closes the previous chunk, so the quoted word starts a new one.
4. A closing double quote closes the chunk on the word carrying it.

Text pasted without spaces is repaired first: `forth,The` becomes `forth, The` and `it."Believe` becomes `it. "Believe`, while `0.99365`, `1,000`, `e.g.` and `7.25p.m.` stay intact.
Straight double quotes alternate open and close by parity.
A token with no letters or digits, such as a spaced en dash, glues to the previous word so it never occupies a chunk of its own.

The pivot word is the middle word of a three-word chunk, the word with more letters in a two-word chunk (tie goes to the first), or the only word.
The pivot letter is the middle letter counting letters only, rounding left for an even count (`Bull` highlights `u`); a word with no letters falls back to its digits.

To inspect the units for any file without opening the GUI:

```sh
uv run rsvp-reader --dump-chunks "book/selfhelp/some book.txt" --chunk-size 3
uv run rsvp-reader --dump-chunks "book/selfhelp/some book.txt" --sentences
```

## Development

```sh
uv sync
uv run pytest            # unit tests plus Tk smoke tests (skipped without a display)
uv run ruff check src tests
uv run ruff format src tests
uv build                 # sdist and wheel under dist/
```

CI runs lint and tests on Linux, macOS and Windows for every push and pull request, and builds the wheel on Linux.

### Releasing

The package version lives only in `__version__` in `src/rsvp_reader/__init__.py`.
To release: bump it, merge, then publish a GitHub release whose tag is `v<version>` (for example `v1.0.1`).
The publish workflow builds the distributions, checks that the tag matches the version, and uploads to PyPI through trusted publishing; no API token is stored anywhere.

Layout under `src/rsvp_reader/`:

| Module | Role |
|---|---|
| `text.py` | Normalization, tokenization, chunk and sentence building, file decoding |
| `pivot.py` | Pivot word and letter selection |
| `session.py` | Reading cursor over units; position survives mode and chunk-size changes |
| `autoplay.py` | WPM ramp and due-time logic driven by an external clock |
| `layout.py` | Pivot box and flow-text geometry |
| `settings.py`, `progress.py`, `storage.py`, `paths.py`, `colors.py` | Validated settings, per-book resume, atomic JSON, config locations, hex color helpers |
| `library.py` | Folder listing |
| `app.py`, `browser_view.py`, `reader_view.py`, `settings_panel.py`, `theme.py` | Tk shell and views |
| `cli.py` | Argument parsing and entry point |

Everything outside the Tk modules is pure and unit tested; the Tk smoke tests drive a real window and assert the rendered pivot geometry from Tk's own bounding boxes.
