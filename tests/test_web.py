from fastapi.testclient import TestClient

from app.main import app
from labelcheck.rules.warning import WARNING_TEXT
from tests.labelgen import render
from tests.test_pipeline_smoke import LINES

c = TestClient(app)


def test_health():
    assert c.get("/health").json()["status"] == "ok"


def test_index_has_three_steps():
    html = c.get("/").text
    assert "Step 1" in html and "Step 2" in html and "Step 3" in html


def test_verify_rejects_non_image():
    r = c.post("/verify", data={"brand": "X", "beverage_type": "spirits"}, files={"image": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 200 and "could not read this image" in r.text.lower()


def test_verify_requires_brand():
    r = c.post("/verify", data={"brand": " "}, files={"image": ("a.png", render(LINES), "image/png")})
    assert "brand name" in r.text.lower()


def test_verify_good_label_renders_pass():
    img = render(LINES, warning=WARNING_TEXT)
    r = c.post(
        "/verify",
        data={"brand": "OLD TOM DISTILLERY", "abv_percent": "45", "net_contents": "750 mL",
              "bottler": "Old Tom Distillery, Bardstown, KY", "beverage_type": "spirits"},
        files={"image": ("l.png", img, "image/png")},
    )
    assert r.status_code == 200 and "Result: <span class=\"pass\">PASS" in r.text and "Checked in" in r.text
