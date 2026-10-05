"""Puts backend/src on the import path so tests import exactly what Lambda imports."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
