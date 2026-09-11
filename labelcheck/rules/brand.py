"""Brand name check.

Dave's case: "STONE'S THROW" on the label and "Stone's Throw" on the application is the
same brand. So matching runs on normalized text and case or punctuation only differences
pass with a note. PASS requires every word of the brand to appear on the best matching
label line; anything merely similar ("Distillers" vs "Distillery") is REVIEW so the agent
makes the call instead of the tool silently deciding.
"""

from rapidfuzz import fuzz

from labelcheck.models import FieldResult, Status
from labelcheck.rules.normalize import normalize, normalize_keep_case

PASS_AT = 92
REVIEW_AT = 75


def _best_line(needle: str, lines: list[str]) -> tuple[int, int]:
    best, idx = 0, -1
    for i, line in enumerate(lines):
        s = fuzz.token_set_ratio(needle, line)
        if s > best:
            best, idx = s, i
    return best, idx


def check_brand(expected: str, ocr_text: str) -> FieldResult:
    exp_n = normalize(expected)
    raw_lines = [normalize_keep_case(line) for line in ocr_text.splitlines() if line.strip()]
    lines = [normalize(line) for line in raw_lines]
    score, idx = _best_line(exp_n, lines)
    found = raw_lines[idx] if idx >= 0 else ""
    conf = round(score / 100, 2)
    base = dict(field="brand", expected=expected, found=found, confidence=conf)
    exact_words = idx >= 0 and set(exp_n.split()) <= set(lines[idx].split())
    if score >= PASS_AT and exact_words:
        note = ""
        exp_flat = normalize_keep_case(expected)
        if found and found != exp_flat:
            if found.upper() == exp_flat.upper():
                note = "Matches; only letter case differs on the label."
            elif normalize(found) == exp_n:
                note = "Matches; punctuation or spacing differs on the label."
        return FieldResult(status=Status.PASS, note=note, **base)
    if score >= REVIEW_AT:
        return FieldResult(
            status=Status.REVIEW,
            note="Possible formatting or spelling difference. Agent confirms.",
            **base,
        )
    return FieldResult(
        status=Status.FAIL, note="Brand name on the label does not match the application.", **base
    )
