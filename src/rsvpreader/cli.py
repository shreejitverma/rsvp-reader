"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rsvpreader import __version__
from rsvpreader.paths import (
    LEGACY_SETTINGS_FILENAME,
    PROGRESS_FILENAME,
    SETTINGS_FILENAME,
    default_book_root,
    legacy_config_dir,
    user_config_dir,
)
from rsvpreader.progress import ProgressStore
from rsvpreader.settings import CHUNK_SIZES, SettingsStore
from rsvpreader.text import build_units, load_book_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rsvpreader",
        description="Spritz-style RSVP reader for plain-text books.",
    )
    parser.add_argument(
        "book_root",
        nargs="?",
        type=Path,
        help="folder containing .txt books (default: ./book or $RSVPREADER_BOOK_ROOT)",
    )
    parser.add_argument(
        "--windowed", action="store_true", help="start in a normal window instead of fullscreen"
    )
    parser.add_argument(
        "--config-dir", type=Path, help="where settings.json and progress.json live"
    )
    parser.add_argument(
        "--dump-chunks",
        metavar="FILE",
        type=Path,
        help="print the reading units for FILE (one per line) and exit; no GUI",
    )
    parser.add_argument(
        "--chunk-size", type=int, choices=CHUNK_SIZES, help="override chunk size for --dump-chunks"
    )
    parser.add_argument(
        "--sentences", action="store_true", help="use sentence mode for --dump-chunks"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def dump_chunks(store: SettingsStore, args: argparse.Namespace) -> int:
    settings = store.load()
    try:
        text = load_book_text(args.dump_chunks)
    except OSError as exc:
        print(f"rsvpreader: cannot read {args.dump_chunks}: {exc}", file=sys.stderr)
        return 1
    units = build_units(
        text,
        sentence_mode=args.sentences or (settings.sentence_mode and not args.chunk_size),
        chunk_size=args.chunk_size or settings.chunk_size,
    )
    for unit in units:
        print(unit)
    print(f"units: {len(units)}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_dir = args.config_dir or user_config_dir()
    legacy_dir = legacy_config_dir()
    settings_store = SettingsStore(
        config_dir / SETTINGS_FILENAME,
        legacy_paths=(legacy_dir / SETTINGS_FILENAME, Path.cwd() / LEGACY_SETTINGS_FILENAME),
    )
    if args.dump_chunks is not None:
        return dump_chunks(settings_store, args)

    if args.book_root is not None:
        book_root = args.book_root.expanduser()
        if not book_root.is_dir():
            print(f"rsvpreader: book folder not found: {book_root}", file=sys.stderr)
            return 2
    else:
        book_root = default_book_root()
        book_root.mkdir(parents=True, exist_ok=True)

    # Imported here so --dump-chunks and --help work on Pythons without tkinter.
    from rsvpreader.app import run_app  # noqa: PLC0415

    return run_app(
        book_root=book_root,
        settings_store=settings_store,
        progress_store=ProgressStore(
            config_dir / PROGRESS_FILENAME, legacy_paths=(legacy_dir / PROGRESS_FILENAME,)
        ),
        fullscreen=not args.windowed,
    )
