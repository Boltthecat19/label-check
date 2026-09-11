"""Tiny label renderer shared by tests (the full generator lives in tools/make_labels.py)."""

import io
import textwrap

from PIL import Image, ImageDraw, ImageFont

BOLD = "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"
REG = "/usr/share/fonts/liberation/LiberationSans-Regular.ttf"


def render(lines: list[str], size=(1200, 1600), warning: str | None = None) -> bytes:
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    big, reg, small = ImageFont.truetype(BOLD, 64), ImageFont.truetype(REG, 36), ImageFont.truetype(REG, 28)
    y = 80
    for i, line in enumerate(lines):
        d.text((80, y), line, fill="black", font=big if i == 0 else reg)
        y += 90 if i == 0 else 56
    if warning:
        y += 30
        for line in textwrap.wrap(warning, 62):
            d.text((80, y), line, fill="black", font=small)
            y += 40
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()
