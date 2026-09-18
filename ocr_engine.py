"""
ocr_engine.py
=============
Text extraction + route-number parsing.

ENGINE CHOICE: Tesseract is the default and the only one recommended for
the Pi Zero 2 W. EasyOCR is included as an optional path because it's
commonly suggested for this kind of project, but it depends on PyTorch,
which on a Zero 2 W (512MB RAM, no GPU) typically costs 2-4 seconds just
to load the model on cold start and 500ms-1.5s per inference even warm —
that alone can consume the entire 1.5s budget before you've done
anything else. Tesseract's `--psm 7` single-line mode on a small, high-
contrast, binarized crop typically runs in 100-400ms on this hardware.

If you later move to a Pi 4/5 or add a Coral/Hailo accelerator, EasyOCR
(or a PaddleOCR-lite model) becomes a reasonable accuracy upgrade — see
SOFTWARE_AND_HARDWARE_GUIDE.md.
"""
import re
import time
import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import pytesseract

import config

logger = logging.getLogger("bus_route.ocr")
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

_ROUTE_PATTERN = re.compile(config.ROUTE_REGEX)


@dataclass
class OcrResult:
    raw_text: str
    route: Optional[str]
    confidence: float  # 0-100
    engine: str
    elapsed_s: float
    # True when `confidence` is a stand-in, not a real measurement (e.g. Windows'
    # OCR API returns no confidence score at all). The UI must label these
    # differently from Tesseract's genuine per-word confidence — never present
    # an estimate as if it were a measured percentage.
    confidence_is_estimated: bool = False


def extract_route(binary_image: np.ndarray, raw_frame: Optional[np.ndarray] = None) -> OcrResult:
    """Run OCR + regex parsing, returning the best route match found."""
    if config.OCR_ENGINE == "easyocr":
        return _extract_with_easyocr(binary_image)
    return _extract_with_tesseract(binary_image, raw_frame=raw_frame)


def _tesseract_pass(binary_image: np.ndarray, psm: int):
    tess_config = (
        f"--psm {psm} -c tessedit_char_whitelist={config.TESSERACT_WHITELIST}"
    )
    data = pytesseract.image_to_data(
        binary_image,
        lang=config.TESSERACT_LANG,
        config=tess_config,
        output_type=pytesseract.Output.DICT,
    )
    words, confidences = [], []
    for text, conf in zip(data["text"], data["conf"]):
        conf = float(conf)
        if text.strip() and conf >= 0:
            words.append(text.strip())
            confidences.append(conf)
    raw_text = " ".join(words)
    mean_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return raw_text, mean_conf


def _extract_with_winocr(binary_image: np.ndarray, raw_frame: Optional[np.ndarray] = None) -> OcrResult:
    t0 = time.monotonic()
    try:
        import winocr
        texts = []

        # Pass 1: Raw image (best for natural text, signs, color boards)
        if raw_frame is not None and raw_frame.size > 0:
            res_raw = winocr.recognize_cv2_sync(raw_frame)
            if res_raw and res_raw.get("text"):
                texts.append(res_raw["text"].strip())

            # Pass 1b: 2x scaled for small fonts / window signs
            h_f, w_f = raw_frame.shape[:2]
            if max(h_f, w_f) < 1200:
                scale = min(2.0, 1600.0 / max(h_f, w_f))
                frame_scaled = cv2.resize(raw_frame, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                res_scaled = winocr.recognize_cv2_sync(frame_scaled)
                if res_scaled and res_scaled.get("text"):
                    texts.append(res_scaled["text"].strip())

        # Pass 2: Binary threshold image (best for high-contrast white-on-black or black-on-white plates)
        if binary_image is not None and binary_image.size > 0:
            img_bgr = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2BGR) if binary_image.ndim == 2 else binary_image.copy()
            res_bin = winocr.recognize_cv2_sync(np.ascontiguousarray(img_bgr))
            if res_bin and res_bin.get("text"):
                texts.append(res_bin["text"].strip())

        # Deduplicate and combine lines
        combined_lines = []
        seen = set()
        for block in texts:
            for line in block.split("\n"):
                clean_l = line.strip()
                if clean_l and len(clean_l) >= 2 and clean_l.lower() not in seen:
                    seen.add(clean_l.lower())
                    combined_lines.append(clean_l)

        raw_text = " ".join(combined_lines)
        route = _parse_route(raw_text)

        # Windows' OCR API (winrt OcrEngine) does not expose any confidence
        # score — there is no real number to report here. Rather than
        # fabricate a specific percentage (which was misleading: it made an
        # unreliable read look precisely measured), report a plain pass/fail
        # signal tied to whether a well-formed route pattern was actually
        # found, and flag it as estimated so the UI never displays it as a
        # genuine measured confidence.
        mean_conf = (config.OCR_MIN_CONFIDENCE + 10.0) if route else 0.0
        elapsed = time.monotonic() - t0
        logger.debug("winocr raw='%s' route=%s estimated_conf=%.1f (%.3fs)", raw_text, route, mean_conf, elapsed)
        return OcrResult(raw_text, route, mean_conf, "winocr", elapsed, confidence_is_estimated=True)
    except Exception as e:
        logger.warning("winocr extraction failed: %s", e)
        return OcrResult("", None, 0.0, "winocr", time.monotonic() - t0, confidence_is_estimated=True)



def _extract_with_tesseract(binary_image: np.ndarray, raw_frame: Optional[np.ndarray] = None) -> OcrResult:
    t0 = time.monotonic()
    try:
        raw_text, mean_conf = _tesseract_pass(binary_image, config.TESSERACT_PSM_PRIMARY)
        if not raw_text:
            raw_text, mean_conf = _tesseract_pass(binary_image, config.TESSERACT_PSM_FALLBACK)

        route = _parse_route(raw_text)
        elapsed = time.monotonic() - t0

        return OcrResult(raw_text, route, mean_conf, "tesseract", elapsed)
    except Exception as e:
        logger.info("Tesseract not available on host (%s). Falling back to Windows OCR...", e)
        return _extract_with_winocr(binary_image, raw_frame=raw_frame)


_easyocr_reader = None  # lazy-loaded singleton, only if OCR_ENGINE == "easyocr"


def _extract_with_easyocr(binary_image: np.ndarray) -> OcrResult:
    global _easyocr_reader
    t0 = time.monotonic()
    if _easyocr_reader is None:
        import easyocr
        _easyocr_reader = easyocr.Reader(["en"], gpu=False)

    results = _easyocr_reader.readtext(binary_image, detail=1)
    if not results:
        return OcrResult("", None, 0.0, "easyocr", time.monotonic() - t0)

    raw_text = " ".join(r[1] for r in results)
    mean_conf = 100.0 * sum(r[2] for r in results) / len(results)
    route = _parse_route(raw_text)
    elapsed = time.monotonic() - t0
    return OcrResult(raw_text, route, mean_conf, "easyocr", elapsed)


def _parse_route(raw_text: str) -> Optional[str]:
    """Pull the most plausible route token out of noisy OCR text."""
    if not raw_text:
        return None

    # 1. Clean out common vehicle plate prefixes (e.g. AP16, DL1P, KA51, TS09) and bus markings (STOP, TATA, SPEED)
    cleaned = re.sub(r'\b[A-Z]{2}\s*\d{1,2}\s*[A-Z]{0,2}\s*\d{0,4}\b', '', raw_text, flags=re.I)
    cleaned = re.sub(r'\b(STOP|KEEP|DISTANCE|FEET|SPEED|TATA|LEYLAND|APSRTC|BMTC|DTC)\b', '', cleaned, flags=re.I)

    # 2. Standard regex: 1-3 digits + optional single letter (e.g. 12, 500A, 21C, 764)
    matches = _ROUTE_PATTERN.findall(cleaned.upper())
    # Filter out lone 0 / O / STOP
    matches = [m for m in matches if m not in ("0", "00", "O")]
    if matches:
        return max(matches, key=len)

    # 3. Fallback search across original raw_text if cleaned was too aggressive
    raw_matches = _ROUTE_PATTERN.findall(raw_text.upper())
    raw_matches = [m for m in raw_matches if m not in ("0", "00", "O") and not re.match(r'^[A-Z]{2}\d+', m)]
    if raw_matches:
        return max(raw_matches, key=len)

    return None

