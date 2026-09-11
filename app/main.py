"""Label Check web app: one page for a single label, one for a batch."""

from pathlib import Path
from typing import Annotated

import pytesseract
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from labelcheck.batch import CSV_COLUMNS, BatchStore, export_csv, parse_csv
from labelcheck.limits import (
    MAX_BATCH_BYTES,
    MAX_BATCH_ROWS,
    OCR_WAIT_SECONDS,
    batch_limiter,
    client_key,
    ocr_slots,
    verify_limiter,
)
from labelcheck.llm import get_llm
from labelcheck.models import Application, BeverageType
from labelcheck.verify import verify

BASE = Path(__file__).parent
VERSION = "0.1.0"
MAX_BYTES = 10 * 1024 * 1024
FIELD_NAMES = {
    "brand": "Brand name",
    "abv": "Alcohol content",
    "net_contents": "Net contents",
    "bottler": "Bottler or producer",
    "origin": "Country of origin",
    "warning": "Government warning",
}

app = FastAPI(title="Label Check", version=VERSION)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
tpl = Jinja2Templates(directory=BASE / "templates")
tpl.env.globals["field_names"] = FIELD_NAMES
batches = BatchStore()


def _error(request: Request, message: str, status: int = 200) -> HTMLResponse:
    return tpl.TemplateResponse(request, "_error.html", {"message": message}, status_code=status)


def _checked(app_fields: Application, data: bytes):
    """Run one verification inside an OCR slot; returns None when the box is saturated."""
    if not ocr_slots.acquire(timeout=OCR_WAIT_SECONDS):
        return None
    try:
        return verify(app_fields, data, llm=get_llm())
    finally:
        ocr_slots.release()


@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION, "tesseract": str(pytesseract.get_tesseract_version())}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return tpl.TemplateResponse(request, "index.html", {"beverages": [b.value for b in BeverageType]})


@app.post("/verify", response_class=HTMLResponse)
async def do_verify(
    request: Request,
    image: Annotated[UploadFile, File()],
    brand: str = Form(""),
    class_type: str = Form(""),
    abv_percent: str = Form(""),
    net_contents: str = Form(""),
    bottler: str = Form(""),
    is_import: str = Form(""),
    origin_country: str = Form(""),
    beverage_type: str = Form("spirits"),
):
    if not verify_limiter.allow(client_key(request)):
        return _error(request, "Too many checks in a short time. Please wait a minute and try again.", 429)
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
        brand=brand,
        class_type=class_type,
        abv_percent=abv,
        net_contents=net_contents,
        bottler=bottler,
        is_import=bool(is_import),
        origin_country=origin_country,
        beverage_type=beverage_type,
    )
    try:
        verdict = await run_in_threadpool(_checked, application, data)
    except Exception:
        return _error(request, "We could not read this image. Try a clearer photo saved as JPG or PNG.")
    if verdict is None:
        return _error(request, "The checker is busy right now. Please try again in a few seconds.", 503)
    return tpl.TemplateResponse(
        request, "_result.html", {"v": verdict, "seconds": f"{verdict.processing_ms / 1000:.1f}"}
    )


@app.get("/batch", response_class=HTMLResponse)
def batch_page(request: Request):
    return tpl.TemplateResponse(request, "batch.html", {"columns": CSV_COLUMNS})


@app.post("/batch", response_class=HTMLResponse)
async def batch_start(
    request: Request,
    sheet: Annotated[UploadFile, File()],
    images: Annotated[list[UploadFile], File()],
):
    if not batch_limiter.allow(client_key(request)):
        return _error(
            request, "Too many batches in a short time. Please wait a few minutes and try again.", 429
        )
    try:
        apps = parse_csv(await sheet.read())
    except (ValueError, UnicodeDecodeError) as e:
        return _error(request, f"We could not use that spreadsheet. {e}")
    if len(apps) > MAX_BATCH_ROWS:
        return _error(
            request, f"That spreadsheet has {len(apps)} rows. Please send at most {MAX_BATCH_ROWS} at a time."
        )
    files: dict[str, bytes] = {}
    total = 0
    for up in images:
        data = await up.read()
        if len(data) > MAX_BYTES:
            return _error(request, f"{up.filename} is larger than 10 MB. Please use smaller images.")
        total += len(data)
        if total > MAX_BATCH_BYTES:
            return _error(
                request, "The images add up to more than 200 MB. Please send fewer or smaller images."
            )
        files[Path(up.filename or "").name] = data
    missing = [a.image for a in apps if a.image not in files]
    if len(missing) == len(apps):
        return _error(request, "None of the image names in the spreadsheet match the uploaded files.")
    job_id = batches.create(apps, files, llm=get_llm())
    return tpl.TemplateResponse(request, "_batch_progress.html", {"job": batches.get(job_id)})


@app.get("/batch/{job_id}", response_class=HTMLResponse)
def batch_status(request: Request, job_id: str):
    job = batches.get(job_id)
    if job is None:
        return _error(request, "That batch has expired or does not exist. Batches are kept for one hour.")
    if not job.finished:
        return tpl.TemplateResponse(request, "_batch_progress.html", {"job": job})
    return tpl.TemplateResponse(request, "_batch_table.html", {"job": job})


@app.get("/batch/{job_id}/export")
def batch_export(job_id: str):
    job = batches.get(job_id)
    if job is None:
        return PlainTextResponse("Batch not found.", status_code=404)
    return PlainTextResponse(
        export_csv(job),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="labelcheck-{job_id}.csv"'},
    )
