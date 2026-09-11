import time

import httpx
from fastapi.testclient import TestClient

from app.main import app
from labelcheck.llm import LlmAssist, get_llm
from labelcheck.models import FieldResult, Status
from labelcheck.rules.warning import WARNING_TEXT
from tests.labelgen import render
from tests.test_pipeline_smoke import LINES

c = TestClient(app)

CSV = (
    "application_id,image,brand,class_type,abv_percent,net_contents,bottler,is_import,origin_country,beverage_type\n"
    "A1,good.png,OLD TOM DISTILLERY,Kentucky Straight Bourbon Whiskey,45,750 mL,"
    '"Old Tom Distillery, Bardstown, KY",no,,spirits\n'
    "A2,bad.png,OLD TOM DISTILLERY,Kentucky Straight Bourbon Whiskey,40,750 mL,"
    '"Old Tom Distillery, Bardstown, KY",no,,spirits\n'
    "A3,missing.png,OLD TOM DISTILLERY,,45,750 mL,,no,,spirits\n"
)


def test_batch_end_to_end():
    good = render(LINES, warning=WARNING_TEXT)
    r = c.post(
        "/batch",
        files=[
            ("sheet", ("apps.csv", CSV.encode(), "text/csv")),
            ("images", ("good.png", good, "image/png")),
            ("images", ("bad.png", good, "image/png")),
        ],
    )
    assert r.status_code == 200 and 'hx-get="/batch/' in r.text
    job_id = r.text.split('hx-get="/batch/')[1].split('"')[0]
    for _ in range(60):
        s = c.get(f"/batch/{job_id}")
        if "Download results" in s.text:
            break
        time.sleep(0.25)
    assert "Download results" in s.text
    assert "A1" in s.text and "A2" in s.text and "missing.png" in s.text
    csv_out = c.get(f"/batch/{job_id}/export").text.splitlines()
    assert csv_out[0].startswith("application_id,overall")
    rows = {line.split(",")[0]: line.split(",")[1] for line in csv_out[1:]}
    assert rows["A1"] == "PASS" and rows["A2"] == "FAIL" and rows["A3"] == "ERROR"


def test_batch_rejects_bad_sheet():
    r = c.post(
        "/batch",
        files=[("sheet", ("apps.csv", b"nope\n1\n", "text/csv")), ("images", ("x.png", b"x", "image/png"))],
    )
    assert "could not use that spreadsheet" in r.text.lower()


def test_llm_off_by_default(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    assert get_llm() is None


def test_llm_opinion_and_timeout():
    def ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "Yes, same brand.\nmore"}}]})

    a = LlmAssist("http://llm", "m", transport=httpx.MockTransport(ok))
    fr = FieldResult(field="brand", status=Status.REVIEW, expected="Stone's Throw", found="STONE'S THROW")
    assert a.opinion(fr, "text") == "Yes, same brand."

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("blocked")

    b = LlmAssist("http://llm", "m", transport=httpx.MockTransport(boom))
    assert b.opinion(fr, "text") is None
