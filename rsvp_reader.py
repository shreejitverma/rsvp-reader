"""Launcher shim kept for `python rsvp_reader.py` (the pre-package entry point).

The real code lives in the `rsvp_reader` package under src/. This file puts src/ ahead of
its own directory on sys.path so the package wins over this same-named module, then
delegates to the CLI. Prefer `uv run rsvp-reader` or `python -m rsvp_reader`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from rsvp_reader.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
