"""Country of origin check, only for imports."""

import re

from labelcheck.models import FieldResult, Status
from labelcheck.rules.normalize import normalize

_RX = re.compile(r"(PRODUCT OF|IMPORTED FROM|MADE IN|PRODUCED IN)\s+([A-Z ]{3,30})")


def check_origin(is_import: bool, country: str, ocr_text: str) -> FieldResult:
    if not is_import:
        return FieldResult(field="origin", status=Status.NOT_CHECKED, note="Not an import.")
    text = normalize(ocr_text)
    c = normalize(country)
    m = _RX.search(text)
    found = m.group(0).strip() if m else ""
    if m and c and c in m.group(2):
        return FieldResult(field="origin", status=Status.PASS, expected=country, found=found, confidence=1.0)
    if m:
        return FieldResult(
            field="origin", status=Status.FAIL, expected=country, found=found,
            note="Country of origin on the label differs from the application.",
        )
    return FieldResult(
        field="origin", status=Status.FAIL, expected=country,
        note="Imported product but no country of origin statement was found on the label.",
    )
