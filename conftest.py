"""Pytest bootstrap for local imports."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent

root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)
