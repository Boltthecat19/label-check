"""Run the whole check: preprocess, OCR, every rule, assemble a Verdict."""

import time

from labelcheck.models import Application, Status, Verdict
from labelcheck.ocr import run_ocr
from labelcheck.preprocess import preprocess
from labelcheck.rules.abv import check_abv
from labelcheck.rules.bottler import check_bottler
from labelcheck.rules.brand import check_brand
from labelcheck.rules.contents import check_contents
from labelcheck.rules.origin import check_origin
from labelcheck.rules.warning import check_warning

LLM_DEADLINE_S = 2.0  # each model call may take up to 3 s, so total stays under 5 s


def verify(app: Application, image_bytes: bytes, llm=None) -> Verdict:
    t0 = time.perf_counter()
    img, warnings = preprocess(image_bytes)
    ocr = run_ocr(img)
    if ocr.mean_conf < 60:
        warnings.append("Low image quality; some text was hard to read. A clearer photo may help.")
    results = [
        check_brand(app.brand, ocr.text),
        check_abv(app.abv_percent, ocr.text, app.beverage_type.value),
        check_contents(app.net_contents, ocr.text),
        check_bottler(app.bottler, ocr.text),
        check_origin(app.is_import, app.origin_country, ocr.text),
        check_warning(ocr.text),
    ]
    if llm is not None:
        # The five second budget wins: ask the model only while there is time left for an answer.
        for r in results:
            if r.status == Status.REVIEW and (time.perf_counter() - t0) < LLM_DEADLINE_S:
                opinion = llm.opinion(r, ocr.text)
                if opinion:
                    r.note = (r.note + " AI opinion: " + opinion).strip()
    return Verdict(
        application_id=app.application_id,
        results=results,
        overall=Verdict.overall_from(results),
        ocr_text=ocr.text,
        processing_ms=int((time.perf_counter() - t0) * 1000),
        warnings=warnings,
    )
