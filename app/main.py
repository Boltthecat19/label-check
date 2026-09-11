"""Label Check web app: one page for a single label, one for a batch."""

from pathlib import Path

import pytesseract
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from labelcheck.llm import get_llm
from labelcheck.models import Application, BeverageType
from labelcheck.verify import verify

BASE = Path(__file__).parent
VERSION = "0.1.0"
MAX_BYTES = 10 * 1024 * 1024
FIELD_NAMES = {
    "brand": "Brand name", "abv": "Alcohol content", "net_contents": "Net contents",
    "bottler": "Bottler or producer", "origin": "Country of origin", "warning": "Government warning",
}

app = FastAPI(title="Label Check", version=VERSION)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
tpl = Jinja2Templates(directory=BASE / "templates")
tpl.env.globals["field_names"] = FIELD_NAMES


def _error(request: Request, message: str) -> HTMLResponse:
    return tpl.TemplateResponse(request, "_error.html", {"message": message})


@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION, "tesseract": str(pytesseract.get_tesseract_version())}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return tpl.TemplateResponse(request, "index.html", {"beverages": [b.value for b in BeverageType]})


@app.post("/verify", response_class=HTMLResponse)
async def do_verify(
    request: Request,
    image: UploadFile = File(...),
    brand: str = Form(""),
    class_type: str = Form(""),
    abv_percent: str = Form(""),
    net_contents: str = Form(""),
    bottler: str = Form(""),
    is_import: str = Form(""),
    origin_country: str = Form(""),
    beverage_type: str = Form("spirits"),
):
    data = await image.read()
    if len(data) > MAX_BYTES:
        return _error(request, "That image is larger than 10 MB. Please use a smaller file.")
    if not brand.strip():
        return _error(request, "Please enter the brand name from the application.")
    try:
        abv = float(abv_percent) if abv_percent.strip() else None
    except ValueError:
        return _error(request, "Alcohol content should be a number like 45 or 12.5.")
    if beverage_type not in [b.value for b in BeverageType]:
        beverage_type = "spirits"
    application = Application(
        brand=brand, class_type=class_type, abv_percent=abv, net_contents=net_contents, bottler=bottler,
        is_import=bool(is_import), origin_country=origin_country, beverage_type=beverage_type,
    )
    try:
        verdict = verify(application, data, llm=get_llm())
    except Exception:
        return _error(request, "We could not read this image. Try a clearer photo saved as JPG or PNG.")
    return tpl.TemplateResponse(
        request, "_result.html", {"v": verdict, "seconds": f"{verdict.processing_ms / 1000:.1f}"}
    )
