import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from labelcheck.limits import RateLimiter
from labelcheck.preprocess import preprocess
from tests.labelgen import render
from tests.test_pipeline_smoke import LINES


def test_rate_limiter_window():
    rl = RateLimiter(limit=3, window=60)
    assert [rl.allow("a") for _ in range(4)] == [True, True, True, False]
    assert rl.allow("b") is True


def test_verify_rate_limited_after_ten():
    c = TestClient(app, headers={"x-forwarded-for": "203.0.113.9"})
    img = render(LINES)
    codes = [
        c.post("/verify", data={"brand": "X"}, files={"image": ("l.png", img, "image/png")}).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [200] * 10 and codes[10] == 429


def test_batch_row_cap():
    c = TestClient(app, headers={"x-forwarded-for": "203.0.113.10"})
    rows = "brand,image\n" + "".join(f"B{i},x.png\n" for i in range(101))
    r = c.post(
        "/batch",
        files=[("sheet", ("a.csv", rows.encode(), "text/csv")), ("images", ("x.png", b"x", "image/png"))],
    )
    assert "at most 100" in r.text


def test_decompression_bomb_refused():
    im = Image.new("1", (20000, 20000))  # 400 MP, 1 bit, tiny on disk
    buf = io.BytesIO()
    im.save(buf, "PNG")
    with pytest.raises((ValueError, Image.DecompressionBombError)):  # Pillow's guard or ours, both refuse
        preprocess(buf.getvalue())
