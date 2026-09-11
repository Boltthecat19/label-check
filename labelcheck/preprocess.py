"""Image cleanup before OCR.

Jenny's ask: labels photographed at angles, bad light, glare. The pipeline is EXIF
rotate, resize, grayscale, contrast equalization (CLAHE, which evens out glare and
shadows), deskew when the text is tilted more than a degree, adaptive threshold.
Everything runs on CPU in well under a second at 2000 px.
"""

import io

import cv2
import numpy as np
from PIL import Image, ImageOps

MAX_SIDE = 2000


def preprocess(image_bytes: bytes) -> tuple[np.ndarray, list[str]]:
    warnings: list[str] = []
    pil = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    h, w = img.shape[:2]
    scale = MAX_SIDE / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    elif max(h, w) < 800:
        warnings.append("The image is small; results may be less reliable.")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    gray = _deskew(gray, warnings)
    binar = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    return binar, warnings


def _deskew(gray: np.ndarray, warnings: list[str]) -> np.ndarray:
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inv = cv2.bitwise_not(otsu)
    coords = np.column_stack(np.where(inv > 0))
    if len(coords) < 500:
        return gray
    raw = cv2.minAreaRect(coords.astype(np.float32))[-1]
    # OpenCV reports the rect angle in (-90, 0] or (0, 90] depending on version; fold to a skew.
    angle = 90 + raw if raw < -45 else (raw - 90 if raw > 45 else raw)
    if abs(angle) < 1 or abs(angle) > 15:
        return gray
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w // 2, h // 2), -angle, 1.0)
    warnings.append(f"The image was rotated {abs(angle):.1f} degrees to straighten the text.")
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
