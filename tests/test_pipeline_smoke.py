
from labelcheck.models import Application, Status
from labelcheck.rules.warning import WARNING_TEXT
from labelcheck.verify import verify
from tests.labelgen import render

LINES = [
    "OLD TOM DISTILLERY",
    "Kentucky Straight Bourbon Whiskey",
    "45% Alc./Vol. (90 Proof)",
    "750 mL",
    "Distilled and bottled by Old Tom Distillery, Bardstown, KY",
]
APP = Application(
    brand="OLD TOM DISTILLERY", class_type="Kentucky Straight Bourbon Whiskey", abv_percent=45.0,
    net_contents="750 mL", bottler="Old Tom Distillery, Bardstown, KY", beverage_type="spirits",
)


def test_good_label_passes():
    img = render(LINES, warning=WARNING_TEXT)
    v = verify(APP, img)
    assert v.overall == Status.PASS, [(r.field, r.status, r.note) for r in v.results] + [v.ocr_text]
    assert v.processing_ms < 5000


def test_title_case_warning_fails():
    img = render(LINES, warning=WARNING_TEXT.replace("GOVERNMENT WARNING:", "Government Warning:"))
    v = verify(APP, img)
    assert v.overall == Status.FAIL
    assert next(r for r in v.results if r.field == "warning").status == Status.FAIL
