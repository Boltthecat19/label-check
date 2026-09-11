"""Test labels come from the same renderer as the fixture generator."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.make_labels import _png  # noqa: E402
from tools.make_labels import render as _render


def render(lines: list[str], warning: str | None = None) -> bytes:
    return _png(_render(lines, warning))
