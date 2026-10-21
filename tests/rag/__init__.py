"""Make ``tests/rag`` a package and expose the fixtures directory."""

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
