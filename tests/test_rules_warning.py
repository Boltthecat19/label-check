from labelcheck.models import Status
from labelcheck.rules.bottler import check_bottler
from labelcheck.rules.origin import check_origin
from labelcheck.rules.warning import WARNING_TEXT, check_warning


def test_warning_exact_pass():
    assert check_warning("OLD TOM\n" + WARNING_TEXT).status == Status.PASS


def test_warning_title_case_header_fails():
    r = check_warning(WARNING_TEXT.replace("GOVERNMENT WARNING:", "Government Warning:"))
    assert r.status == Status.FAIL and "caps" in r.note.lower()


def test_warning_altered_wording_fails_with_diff():
    r = check_warning(WARNING_TEXT.replace("birth defects", "birth problems"))
    assert r.status == Status.FAIL and "PROBLEMS" in r.note


def test_warning_missing_fails():
    assert check_warning("OLD TOM 45%").status == Status.FAIL


def test_warning_note_mentions_bold():
    assert "bold" in check_warning(WARNING_TEXT).note.lower()


def test_warning_tolerates_line_breaks():
    assert check_warning(WARNING_TEXT.replace(" ", "\n")).status == Status.PASS


def test_bottler_pass():
    r = check_bottler("Old Tom Distillery, Bardstown, KY", "Distilled and bottled by Old Tom Distillery, Bardstown, KY")
    assert r.status == Status.PASS


def test_bottler_review_no_phrase():
    assert check_bottler("Old Tom Distillery", "Old Tom Distillery Bardstown").status == Status.REVIEW


def test_bottler_fail():
    assert check_bottler("Blue Heron Imports", "Bottled by Old Tom Distillery").status == Status.FAIL


def test_origin_not_checked():
    assert check_origin(False, "", "x").status == Status.NOT_CHECKED


def test_origin_pass():
    assert check_origin(True, "Scotland", "PRODUCT OF SCOTLAND").status == Status.PASS


def test_origin_fail():
    assert check_origin(True, "Scotland", "OLD TOM").status == Status.FAIL
