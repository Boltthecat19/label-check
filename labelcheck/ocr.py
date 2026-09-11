"""Tesseract wrapper. Returns text, mean word confidence, and elapsed time."""

import time
from dataclasses import dataclass

import numpy as np
import pytesseract


@dataclass
class OcrResult:
    text: str
    mean_conf: float
    ms: int


def _data(img: np.ndarray, psm: int) -> dict:
    return pytesseract.image_to_data(
        img, lang="eng", config=f"--psm {psm}", output_type=pytesseract.Output.DICT
    )


def run_ocr(img: np.ndarray) -> OcrResult:
    t0 = time.perf_counter()
    psm = 6
    data = _data(img, psm)
    words = [w for w, c in zip(data["text"], data["conf"]) if str(w).strip() and float(c) >= 0]
    if len(words) < 20:
        psm = 11
        data = _data(img, psm)
    text = pytesseract.image_to_string(img, lang="eng", config=f"--psm {psm}")
    confs = [float(c) for c, w in zip(data["conf"], data["text"]) if str(w).strip() and float(c) >= 0]
    mean = sum(confs) / len(confs) if confs else 0.0
    return OcrResult(text=text, mean_conf=mean, ms=int((time.perf_counter() - t0) * 1000))
