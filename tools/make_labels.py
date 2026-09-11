"""Render synthetic test labels from tools/labels.yaml.

Each entry becomes a clean PNG plus four augmented variants (rotated, blurred, glare,
low quality JPEG) so the tests exercise Jenny's bad photo cases. Writes manifest.json.

Usage: python tools/make_labels.py tests/fixtures
"""

import io
import json
import sys
import textwrap
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from labelcheck.rules.warning import WARNING_TEXT  # noqa: E402

BOLD = "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"
REG = "/usr/share/fonts/liberation/LiberationSans-Regular.ttf"
PHRASE = {"spirits": "Distilled and bottled by", "wine": "Produced and bottled by", "beer": "Brewed and bottled by"}


def lines_for(e: dict) -> tuple[list[str], str | None]:
    d = e.get("defect")
    brand = e.get("label_brand", e["brand"])
    if d == "brand_wrong":
        brand = "BLUE HERON ALE"
    if d == "brand_near":
        brand = "OLD TOM DISTILLERY"
    abv = e.get("abv")
    if d == "abv_wrong" and abv is not None:
        abv = abv - 5
    proof = e.get("proof")
    if d == "proof_mismatch" and proof:
        proof = proof - 10
    out = [brand, e["class_type"]]
    if abv is not None:
        out.append(f"{abv:g}% Alc./Vol." + (f" ({proof} Proof)" if proof else ""))
    if d != "contents_missing":
        out.append(e["net_contents"])
    if d != "bottler_missing":
        out.append(f"{PHRASE[e['beverage_type']]} {e['bottler']}")
    if e.get("is_import") and d != "origin_missing":
        out.append(f"Product of {e['origin_country']}")
    warning = WARNING_TEXT
    if d == "warning_title_case":
        warning = warning.replace("GOVERNMENT WARNING:", "Government Warning:")
    elif d == "warning_wording":
        warning = warning.replace("birth defects", "birth problems")
    elif d == "warning_missing":
        warning = None
    return out, warning


def render(lines: list[str], warning: str | None) -> Image.Image:
    im = Image.new("RGB", (1200, 1600), "white")
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
    return im


def augment(im: Image.Image) -> dict[str, bytes]:
    out = {}
    out["rot"] = _png(im.rotate(5, expand=True, fillcolor="white", resample=Image.BICUBIC))
    out["blur"] = _png(im.filter(ImageFilter.GaussianBlur(1.2)))
    glare = Image.new("L", im.size, 0)
    gd = ImageDraw.Draw(glare)
    for r in range(600, 0, -20):
        gd.ellipse((1000 - r, 100 - r, 1000 + r, 100 + r), fill=int(200 * (1 - r / 600)))
    white = Image.new("RGB", im.size, "white")
    out["glare"] = _png(Image.composite(white, im, glare))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=40)
    out["jpg40"] = buf.getvalue()
    return out


def _png(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def main(out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = yaml.safe_load((Path(__file__).parent / "labels.yaml").read_text())
    manifest = []
    for e in entries:
        lines, warning = lines_for(e)
        im = render(lines, warning)
        app = {
            "application_id": e["id"], "brand": e["brand"], "class_type": e["class_type"],
            "abv_percent": e.get("abv"), "net_contents": e["net_contents"], "bottler": e["bottler"],
            "is_import": bool(e.get("is_import")), "origin_country": e.get("origin_country", ""),
            "beverage_type": e["beverage_type"],
        }
        files = {"clean": _png(im), **augment(im)}
        for variant, data in files.items():
            ext = "jpg" if variant == "jpg40" else "png"
            name = f"{e['id']}_{variant}.{ext}"
            (out_dir / name).write_bytes(data)
            manifest.append({"file": name, "variant": variant, "application": app,
                             "expect": e.get("expect", {}), "overall": e["overall"]})
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


if __name__ == "__main__":
    m = main(Path(sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures"))
    print(f"wrote {len(m)} images")
