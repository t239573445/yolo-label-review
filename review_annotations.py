#!/usr/bin/env python3
"""Run a source checkout without installing the package itself."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from yolo_review.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
