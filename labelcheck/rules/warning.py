"""Government warning statement check (27 CFR 16.21).

Jenny's rule: exact wording, and the "GOVERNMENT WARNING:" header in all caps. Checks run
in order: locate the statement, header caps, body text exact after whitespace
normalization with a word diff on failure. Bold cannot be seen by OCR, so every result
says so instead of pretending.
"""

import difflib
import re

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

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
            field="warning",
            status=Status.FAIL,
            expected=WARNING_TEXT,
            found=seg[:120],
            note="Government warning statement not found on the label." + _BOLD,
        )
    header = re.match(r"GOVERNMENT WARNING([:;.,]?)", seg)
    if not header:
        shown = seg[: len(_HEADER)]
        return FieldResult(
            field="warning",
            status=Status.FAIL,
            expected=WARNING_TEXT,
            found=seg[:160],
            confidence=0.9,
            note=f"Header must read exactly 'GOVERNMENT WARNING:' in all caps; the label shows '{shown}'."
            + _BOLD,
        )
    punct = header.group(1)
    punct_note = (
        ""
        if punct == ":"
        else f" The colon after the header was read as '{punct or ' '}'; confirm it is a colon."
    )
    exp_n, seg_n = normalize(WARNING_TEXT), normalize(seg)
    if seg_n.startswith(exp_n):
        if punct_note:
            return FieldResult(
                field="warning",
                status=Status.REVIEW,
                expected=WARNING_TEXT,
                found=seg[: len(WARNING_TEXT)],
                confidence=0.95,
                note="Statement text is exact." + punct_note + _BOLD,
            )
        return FieldResult(
            field="warning",
            status=Status.PASS,
            expected=WARNING_TEXT,
            found=seg[: len(WARNING_TEXT)],
            confidence=1.0,
            note="Statement text is exact." + _BOLD,
        )
    window = seg_n[: len(exp_n) + 10]
    ratio = fuzz.ratio(exp_n, window)
    diff = [d for d in difflib.ndiff(exp_n.split(), window.split()) if d[0] in "+-"]
    shown = " ".join(diff[:12])
    found = seg[: len(WARNING_TEXT) + 10]
    if _looks_like_ocr_noise(diff):
        return FieldResult(
            field="warning",
            status=Status.REVIEW,
            expected=WARNING_TEXT,
            found=found,
            confidence=round(ratio / 100, 2),
            note=f"Statement nearly matches; the differences look like OCR misreads ({shown}). "
            "Agent confirms the wording visually." + _BOLD,
        )
    return FieldResult(
        field="warning",
        status=Status.FAIL,
        expected=WARNING_TEXT,
        found=found,
        confidence=round(ratio / 100, 2),
        note=f"Statement wording differs from the required text. Differences: {shown}." + _BOLD,
    )


def _looks_like_ocr_noise(diff: list[str]) -> bool:
    """True when every differing word is a small edit of its neighbor or a tiny stray token.

    'tisk' for 'risk' and 'impalrs' for 'impairs' are noise. 'problems' for 'defects' is a
    real wording change and must fail.
    """
    removed = [d[2:] for d in diff if d[0] == "-"]
    added = [d[2:] for d in diff if d[0] == "+"]
    pairs = list(zip(removed, added, strict=False))  # extra tokens are judged as strays below
    for a, b in pairs:
        if Levenshtein.distance(a, b) > max(1, min(len(a), len(b)) // 4 + 1):
            return False
    strays = removed[len(pairs) :] + added[len(pairs) :]
    return all(len(s) <= 2 for s in strays)
