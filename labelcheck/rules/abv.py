"""Alcohol content check: percent, with proof cross checked when present."""

import re

from labelcheck.models import FieldResult, Status
from labelcheck.rules.normalize import normalize

_PCT = re.compile(r"(\d{1,2}(?:\.\d)?)\s*%\s*(?:ALC|ABV|ALCOHOL|VOL)")
_PROOF = re.compile(r"(\d{2,3})\s*PROOF")


def check_abv(expected: float | None, ocr_text: str, beverage: str) -> FieldResult:
    if expected is None:
        return FieldResult(
            field="abv", status=Status.NOT_CHECKED, note="No alcohol content on the application."
        )
    exp_s = f"{expected:g}%"
    text = normalize(ocr_text)
    pct_m = _PCT.search(text)
    proof_m = _PROOF.search(text)
    if not pct_m:
        if beverage == "spirits":
            return FieldResult(
                field="abv", status=Status.FAIL, expected=exp_s,
                note="No alcohol content found on the label.",
            )
        return FieldResult(
            field="abv", status=Status.REVIEW, expected=exp_s,
            note="No alcohol content found on the label. Some beer and wine labels are exempt; agent confirms.",
        )
    pct = float(pct_m.group(1))
    found = f"{pct:g}%" + (f" ({proof_m.group(1)} proof)" if proof_m else "")
    if abs(pct - expected) > 0.1:
        return FieldResult(
            field="abv", status=Status.FAIL, expected=exp_s, found=found, confidence=1.0,
            note="Alcohol content on the label differs from the application.",
        )
    if proof_m and abs(int(proof_m.group(1)) - 2 * pct) > 1:
        return FieldResult(
            field="abv", status=Status.REVIEW, expected=exp_s, found=found, confidence=0.8,
            note="Percent matches but proof is not twice the percent. Agent confirms.",
        )
    return FieldResult(field="abv", status=Status.PASS, expected=exp_s, found=found, confidence=1.0)
