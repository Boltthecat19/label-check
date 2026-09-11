"""Bottler or producer check: the name must match and a 'bottled by' style phrase must exist."""

from rapidfuzz import fuzz

from labelcheck.models import FieldResult, Status
from labelcheck.rules.normalize import normalize, normalize_keep_case

_PHRASES = (
    "BOTTLED BY", "PRODUCED BY", "DISTILLED BY", "IMPORTED BY", "BREWED BY",
    "VINTED BY", "MADE BY", "BOTTLED FOR", "CELLARED BY", "BLENDED BY",
)


def check_bottler(expected: str, ocr_text: str) -> FieldResult:
    if not expected.strip():
        return FieldResult(field="bottler", status=Status.NOT_CHECKED)
    text = normalize(ocr_text)
    score = fuzz.token_set_ratio(normalize(expected), text)
    has_phrase = any(p in text for p in _PHRASES)
    found = next(
        (normalize_keep_case(line) for line in ocr_text.splitlines() if any(p in normalize(line) for p in _PHRASES)),
        "",
    )
    base = dict(field="bottler", expected=expected, found=found, confidence=round(score / 100, 2))
    if score >= 85 and has_phrase:
        return FieldResult(status=Status.PASS, **base)
    if score >= 65:
        return FieldResult(
            status=Status.REVIEW,
            note="Bottler name found but no 'bottled by' style phrase, or the wording differs. Agent confirms.",
            **base,
        )
    return FieldResult(
        status=Status.FAIL, note="Bottler or producer on the label does not match the application.", **base
    )
