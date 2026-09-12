"""Launcher shim so `python rsvpreader.py` works from a checkout without installing.

The real code lives in the `rsvpreader` package under src/. This file puts src/ ahead of
its own directory on sys.path so the package wins over this same-named module, then
delegates to the CLI. Prefer `uv run rsvpreader` or `python -m rsvpreader`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from rsvpreader.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
