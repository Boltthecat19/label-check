"""Tesseract wrapper. One OCR pass returns text, mean word confidence, and elapsed time."""

import time
from dataclasses import dataclass
from itertools import groupby

import numpy as np
import pytesseract


@dataclass
class OcrResult:
    text: str
    mean_conf: float
    ms: int


def _words(img: np.ndarray, psm: int) -> list[tuple[tuple[int, int, int], str, float]]:
    """(block, paragraph, line) position, word, confidence for every recognized word."""
    d = pytesseract.image_to_data(img, lang="eng", config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    return [
        ((b, p, ln), w, float(c))
        for b, p, ln, w, c in zip(
            d["block_num"], d["par_num"], d["line_num"], d["text"], d["conf"], strict=True
        )
        if str(w).strip() and float(c) >= 0
    ]


def _text(words: list[tuple[tuple[int, int, int], str, float]]) -> str:
    """Rebuild lines and paragraphs so the rules see the same layout Tesseract saw."""
    out, prev_par = [], None
    for (block, par, _), line in groupby(words, key=lambda w: w[0]):
        if prev_par is not None and (block, par) != prev_par:
            out.append("")
        out.append(" ".join(w for _, w, _ in line))
        prev_par = (block, par)
    return "\n".join(out)


def run_ocr(img: np.ndarray) -> OcrResult:
    t0 = time.perf_counter()
    words = _words(img, psm=3)  # automatic layout keeps the oversized brand line that psm 6 drops
    if len(words) < 20:
        words = _words(img, psm=11)  # sparse text fallback for labels with little copy
    confs = [c for _, _, c in words]
    mean = sum(confs) / len(confs) if confs else 0.0
    return OcrResult(text=_text(words), mean_conf=mean, ms=int((time.perf_counter() - t0) * 1000))
