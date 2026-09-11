"""Net contents check. Everything is normalized to millilitres before comparing."""

import re

from labelcheck.models import FieldResult, Status
from labelcheck.rules.normalize import normalize

_ML = {"ML": 1.0, "L": 1000.0, "CL": 10.0, "FLOZ": 29.5735, "OZ": 29.5735}
_RX = re.compile(r"(\d+(?:\.\d+)?)\s*(FL\.? ?OZ\.?|ML|CL|L|OZ)\b")


def _find(text: str) -> tuple[float | None, str]:
    m = _RX.search(normalize(text))
    if not m:
        return None, ""
    unit = m.group(2).replace(" ", "").replace(".", "")
    return round(float(m.group(1)) * _ML.get(unit, 0.0), 1), m.group(0)


def parse_ml(s: str) -> float | None:
    ml, _ = _find(s)
    return ml or None


def check_contents(expected: str, ocr_text: str) -> FieldResult:
    exp_ml = parse_ml(expected)
    if exp_ml is None:
        return FieldResult(
            field="net_contents", status=Status.NOT_CHECKED, expected=expected,
            note="Could not read net contents on the application.",
        )
    found_ml, found = _find(ocr_text)
    if found_ml is None:
        return FieldResult(
            field="net_contents", status=Status.REVIEW, expected=expected,
            note="No net contents found on the label. Agent confirms.",
        )
    if abs(found_ml - exp_ml) <= max(1.0, exp_ml * 0.01):
        return FieldResult(
            field="net_contents", status=Status.PASS, expected=expected, found=found, confidence=1.0
        )
    return FieldResult(
        field="net_contents", status=Status.FAIL, expected=expected, found=found, confidence=1.0,
        note="Net contents on the label differ from the application.",
    )
