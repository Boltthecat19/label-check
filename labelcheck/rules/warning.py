"""Government warning statement check (27 CFR 16.21).

Jenny's rule: exact wording, and the "GOVERNMENT WARNING:" header in all caps. Checks run
in order: locate the statement, header caps, body text exact after whitespace
normalization with a word diff on failure. Bold cannot be seen by OCR, so every result
says so instead of pretending.
"""

import difflib

from rapidfuzz import fuzz

from labelcheck.models import FieldResult, Status
from labelcheck.rules.normalize import normalize, normalize_keep_case

WARNING_TEXT = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or operate "
    "machinery, and may cause health problems."
)
_HEADER = "GOVERNMENT WARNING:"
_BOLD = " Bold formatting cannot be verified by OCR; agent confirms visually."


def _locate(raw: str) -> str:
    flat = normalize_keep_case(raw)
    upper = flat.upper()
    i = upper.find("GOVERNMENT WARNING")
    if i < 0:
        i = upper.find("SURGEON GENERAL")
        if i < 0:
            return ""
        i = max(0, i - 40)
    return flat[i : i + len(WARNING_TEXT) + 60]


def check_warning(ocr_text_raw: str) -> FieldResult:
    seg = _locate(ocr_text_raw)
    if not seg or fuzz.partial_ratio(normalize(seg), normalize(WARNING_TEXT)) < 60:
        return FieldResult(
            field="warning", status=Status.FAIL, expected=WARNING_TEXT, found=seg[:120],
            note="Government warning statement not found on the label." + _BOLD,
        )
    if not seg.startswith(_HEADER):
        shown = seg[: len(_HEADER)]
        return FieldResult(
            field="warning", status=Status.FAIL, expected=WARNING_TEXT, found=seg[:160], confidence=0.9,
            note=f"Header must read exactly 'GOVERNMENT WARNING:' in all caps; the label shows '{shown}'." + _BOLD,
        )
    exp_n, seg_n = normalize(WARNING_TEXT), normalize(seg)
    if seg_n.startswith(exp_n):
        return FieldResult(
            field="warning", status=Status.PASS, expected=WARNING_TEXT,
            found=seg[: len(WARNING_TEXT)], confidence=1.0, note="Statement text is exact." + _BOLD,
        )
    window = seg_n[: len(exp_n) + 10]
    ratio = fuzz.ratio(exp_n, window)
    diff = [d for d in difflib.ndiff(exp_n.split(), window.split()) if d[0] in "+-"]
    shown = " ".join(diff[:12])
    return FieldResult(
        field="warning", status=Status.FAIL, expected=WARNING_TEXT, found=seg[: len(WARNING_TEXT) + 10],
        confidence=round(ratio / 100, 2),
        note=f"Statement wording differs from the required text. Differences: {shown}." + _BOLD,
    )
