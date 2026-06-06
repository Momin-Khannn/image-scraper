"""Compatibility launcher for the packaged image scraper.

Example:
    python "Data Scapping from websites ( pictures ).py" https://example.com --output-dir output
"""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from image_scraper.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
