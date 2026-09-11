from labelcheck.models import Status
from labelcheck.rules.abv import check_abv
from labelcheck.rules.brand import check_brand
from labelcheck.rules.contents import check_contents, parse_ml

OCR = (
    "OLD TOM DISTILLERY\nKentucky Straight Bourbon Whiskey\n45% Alc./Vol. (90 Proof)\n750 mL\n"
    "Distilled and bottled by Old Tom Distillery, Bardstown, KY"
)


def test_brand_exact():
    assert check_brand("OLD TOM DISTILLERY", OCR).status == Status.PASS


def test_brand_case_only_passes_with_note():
    r = check_brand("Stone's Throw", "STONE'S THROW\nRye Whiskey")
    assert r.status == Status.PASS and "case" in r.note.lower()


def test_brand_review_band():
    assert check_brand("Old Tom Distillers", "OLD TOM DISTILLERY\n").status == Status.REVIEW


def test_brand_fail():
    assert check_brand("Blue Heron", OCR).status == Status.FAIL


def test_abv_pass():
    assert check_abv(45.0, OCR, "spirits").status == Status.PASS


def test_abv_mismatch():
    assert check_abv(40.0, OCR, "spirits").status == Status.FAIL


def test_abv_proof_mismatch():
    assert check_abv(45.0, "45% ALC/VOL (80 PROOF)", "spirits").status == Status.REVIEW


def test_abv_missing_spirits_fail():
    assert check_abv(45.0, "OLD TOM", "spirits").status == Status.FAIL


def test_abv_missing_beer_review():
    assert check_abv(5.0, "OLD TOM", "beer").status == Status.REVIEW


def test_parse_ml():
    assert parse_ml("750 mL") == 750
    assert parse_ml("1 L") == 1000
    assert abs(parse_ml("25.4 fl oz") - 751.2) < 1


def test_contents_pass():
    assert check_contents("750 mL", OCR).status == Status.PASS


def test_contents_fail():
    assert check_contents("1 L", OCR).status == Status.FAIL


def test_contents_unparseable_review():
    assert check_contents("750 mL", "OLD TOM").status == Status.REVIEW
