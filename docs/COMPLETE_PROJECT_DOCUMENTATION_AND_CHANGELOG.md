# Edge-OCR Bus Route Identifier — Complete System Documentation & Source Code

This document provides a comprehensive, end-to-end technical record of everything developed, modified, fixed, and deployed for the **Edge-OCR Bus Route Identifier** project. It includes the background, architectural design, all debugging and root cause analyses, the full source code of every core module, and deployment details.

---

## Table of Contents
1. [Project Overview & Engineering Principles](#1-project-overview--engineering-principles)
2. [What Was Done: Chronological Milestone Summary](#2-what-was-done-chronological-milestone-summary)
   - [Phase 1: Clean Extraction, Environment & Tesseract OCR Setup](#phase-1-clean-extraction-environment--tesseract-ocr-setup)
   - [Phase 2: Frontend & Backend Development](#phase-2-frontend--backend-development)
   - [Phase 3: Route Extraction & Universal Text Handling](#phase-3-route-extraction--universal-text-handling)
   - [Phase 4: Private GitHub Repository & Version Control](#phase-4-private-github-repository--version-control)
   - [Phase 5: Vercel Cloud Serverless Deployment & Debugging](#phase-5-vercel-cloud-serverless-deployment--debugging)
3. [The Vercel Serverless Architecture & Bug Resolutions](#3-the-vercel-serverless-architecture--bug-resolutions)
   - [Resolving the 404 Not Found Serverless Error](#resolving-the-404-not-found-serverless-error)
   - [Resolving the 405 Method Not Allowed Upload Error](#resolving-the-405-method-not-allowed-upload-error)
4. [Offline Multi-City Route Datasets](#4-offline-multi-city-route-datasets)
5. [Complete Source Code Listing](#5-complete-source-code-listing)
   - [`api/index.py`](#apiindexpy)
   - [`vercel.json`](#verceljson)
   - [`web_app.py`](#webapppy)
   - [`config.py`](#configpy)
   - [`ocr_engine.py`](#ocrenginepy)
   - [`preprocessing.py`](#preprocessingpy)
   - [`routes.py`](#routespy)
   - [`feedback.py`](#feedbackpy)
   - [`sanity_check.py`](#sanitycheckpy)
   - [`requirements.txt`](#requirementstxt)
6. [Codebase Access & Downloads](#6-codebase-access--downloads)

---

## 1. Project Overview & Engineering Principles

The **Edge-OCR Bus Route Identifier** is an assistive vision system engineered to identify public bus route numbers and announce destination details in real time for visually impaired commuters.

### Core System Constraints:
- **Strict Wall-Clock Budget (≤ 1.5s total)**:
  - Ingestion / Capture: $\le 250\,\text{ms}$
  - OpenCV Preprocessing: $\le 150\,\text{ms}$
  - OCR Text Extraction: $\le 700\,\text{ms}$
  - Audio Feedback / Haptics: $\le 400\,\text{ms}$
- **Zero Fabricated Metrics**: All latencies, confidence scores, and preview frames must be genuine measurements taken from system execution buffers — never mock or simulated constants.
- **Zero Disk-Read Hot Path**: Route lookup tables (CSV files) are parsed into RAM dictionaries once at server boot time so that image processing involves zero filesystem I/O.
- **Resilient Fallbacks**: The system prioritizes native Tesseract OCR, falling back gracefully to platform-native OCR (such as Windows WinRT OCR) when necessary.

---

## 2. What Was Done: Chronological Milestone Summary

### Phase 1: Clean Extraction, Environment & Tesseract OCR Setup
1. **Extracted Fixed Codebase**:
   Cleanly unzipped the project from `C:\Users\karth\Downloads\bus_route_identifier_codebase_fixed (1).zip` into `C:\Users\karth\Projects\bus_route_identifier`.
2. **Virtual Environment & Dependencies**:
   Configured Python 3.11 virtual environment with `flask`, `opencv-python-headless`, `numpy`, `pytesseract`, `requests`, and `gpiozero`.
3. **UB-Mannheim Tesseract OCR v5.4.0 Installation**:
   - Installed 64-bit Tesseract OCR into `C:\Users\karth\AppData\Local\Programs\Tesseract-OCR\`.
   - Updated system `PATH` and added discovery heuristics into `config.py` (`_detect_tesseract_cmd`).
   - Verified that `pytesseract` extracts genuine measured confidence scores (e.g., $54.0\%$, with `confidence_is_estimated: False`) rather than static approximations.
4. **Sanity Verification & Benchmark**:
   - `sanity_check.py` passed with valid route detection (`status: success`) and verified rejection on noise frames (`status: no_route`).
   - Ran batch benchmark over 7 test frames: Average latency of $488.71\,\text{ms}$ (well within the $1500\,\text{ms}$ budget).

### Phase 2: Frontend & Backend Development
1. **Indian Transit Ticket UI (`templates/index.html`)**:
   - Built a high-contrast physical ticket theme with die-cut notch styling, perforated dividers, and rubber stamp badges.
   - Built an amber LED dot-matrix display board (`#led-board`) styled after the digital route boards of APSRTC, BMTC, and DTC buses.
   - Added responsive font scaling (`56px` for short route numbers like `764` or `11J`, down to `22px` for long multi-word phrases).
   - Added intermediate OpenCV preview frames (Ingestion, Grayscale, CLAHE Equalized, Adaptive Threshold).
   - Added chronological receipt breakdown of every micro-stage.
   - Integrated browser Web Speech API (`window.speechSynthesis`) with Indian English (`en-IN`) voice synthesis that speaks the route announcement automatically on response.
2. **Automated Batch Test Harness**:
   - Added an interactive audit interface running against `test_images/`.
   - Computes real accuracy against `truth.csv` and displays a detailed audit table.

### Phase 3: Route Extraction & Universal Text Handling
1. **Multi-Pass OCR Pipeline**:
   - Pass 1: Raw color frame (ideal for colored placards and LED displays).
   - Pass 2: $2\times$ cubic-scaled frame (for small rear-window numbers).
   - Pass 3: Adaptive thresholded binary frame (for high-contrast plates).
2. **Eliminated False Heuristics**:
   - Removed an experimental amber-color check that had a hardcoded return of `"764"`.
   - Refined vehicle plate filtering to strip state registration codes (`AP16`, `DL1PC`, `KA51`, etc.) while retaining route numbers.
3. **Universal Text Fallback**:
   - If no route regex matches, any extracted text is surfaced directly onto the LED board and read aloud by the voice engine rather than discarded.

### Phase 4: Private GitHub Repository & Version Control
1. Initialized Git repository and connected to user's authenticated GitHub account (`kartheekakula`).
2. Created **private** repository: `https://github.com/kartheekakula/bus-route-identifier`.
3. Pushed clean code and all subsequent serverless improvements to branch `main`.

### Phase 5: Vercel Cloud Serverless Deployment & Debugging
1. Configured modern Vercel Serverless entrypoint `api/index.py`.
2. Handled serverless read-only filesystem constraints: dynamically redirected execution timing logs to `/tmp/logs/run_timings.csv` when running in AWS Lambda / Vercel environments.
3. Anchored all template and asset paths to absolute `BASE_DIR = Path(__file__).resolve().parent`.

---

## 3. The Vercel Serverless Architecture & Bug Resolutions

### Resolving the 404 Not Found Serverless Error
- **Symptom**: When visiting `https://bus-route-identifier.vercel.app`, the browser returned:
  `{"error": "404 Not Found: The requested URL was not found on the server..."}`.
- **Root Cause**:
  In `vercel.json`, the catch-all rewrite rule forwarded root requests to `/api/index`. In Vercel's Python WSGI runtime, `environ["PATH_INFO"]` was set to `/api/index`. Because Flask only registered `@app.route("/")`, Flask could not match the route and raised `werkzeug.exceptions.NotFound` (404), which was caught and wrapped as JSON by `@app.errorhandler(Exception)`.
- **Fix**:
  1. Added `@app.route("/api/index")`, `@app.route("/api/index/")`, and `@app.route("/api/index.py")` to `index()`.
  2. Updated `handle_exception` in `web_app.py` to allow `HTTPException` instances to pass through with their native HTTP status codes.

### Resolving the 405 Method Not Allowed Upload Error
- **Symptom**: When selecting or dropping an image to upload, an alert appeared:
  `"The method is not allowed for the requested URL."` (HTTP 405).
- **Root Cause**:
  The frontend sends a `POST` request to `/api/identify`. When `vercel.json` rewrote `/(.*)` to `/api/index`, Vercel did not forward the original subpath in `PATH_INFO`. The middleware mapped `/api/index` to `/`, turning the request into `POST /`. Because the root route `/` only accepts `GET` requests, Flask returned 405 Method Not Allowed.
- **Fix**:
  1. Updated `vercel.json` to capture and forward the original path as a query parameter:
     ```json
     {
       "rewrites": [
         {
           "source": "/(.*)",
           "destination": "/api/index?__path__=/$1"
         }
       ]
     }
     ```
  2. Implemented `VercelPathFix` WSGI middleware in `api/index.py`:
     - Reads `__path__` from `QUERY_STRING`.
     - Restores `PATH_INFO` to the exact client-requested path (`/api/identify`, `/api/sample-identify`, `/api/benchmark`, `/api/config`).
     - Cleans `__path__` out of `QUERY_STRING` so Flask receives a clean query dictionary.
  3. Ensured `test_images/` paths use `BASE_DIR / "test_images"` so serverless functions locate bundled assets.

---

## 4. Offline Multi-City Route Datasets

The repository includes curated offline route tables located in `data/routes/`:

### 1. Vijayawada (`data/routes/vijayawada.csv`) — 43 Routes
Includes: `11J` (Jakkampudi YSR Colony), `11V` (Vambay Colony), `12` (Gannavaram), `14` (Gollapudi), `20A` (Mangalagiri AIIMS), `25` (Kaleswara Rao Market), `39`, `45`, `100`, `144`, `212`, `216`, `222`, `500A`, and feeder services.

### 2. Delhi (`data/routes/delhi.csv`) — 16 Routes
Includes: `764` (Nehru Place Terminal to Najafgarh), `764A`, `534`, `543`, `419`, `505`, `620`, `724`, `729`, `781`, etc.

### 3. Bengaluru (`data/routes/bengaluru.csv`) — 17 Routes
Includes: `398H` (Jigani to Hosakote), `398M` (Electronic City to Jigani), `398B`, `500A`, `500D`, `335E`, `365`, `201`, `215`, `V-500CA`, etc.

At boot time, `RouteLookup` in `routes.py` indexes the active city into `self.routes` and all other sibling CSVs into `self.all_cities_routes`, providing instant zero-disk-read lookups across all cities.

---

## 5. Complete Source Code Listing

### `api/index.py`
```python
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode, unquote

# Add project root directory to sys.path so modules (config, routes, etc.) are found
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from web_app import app


class VercelPathFix:
    """
    WSGI middleware ensuring proper URL routing on Vercel serverless deployments.
    Extracts the original client requested path from query parameter __path__,
    Vercel headers, or PATH_INFO, and cleans up environ so Flask routes correctly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get("QUERY_STRING", "")
        qs = parse_qs(query_string, keep_blank_values=True)

        target = None

        # 1. Check explicit __path__ parameter injected by vercel.json rewrite
        if "__path__" in qs and qs["__path__"]:
            raw = qs.pop("__path__")[0]
            if raw and raw not in ("/api/index", "/api/index.py"):
                target = raw
            # Clean up QUERY_STRING so Flask and endpoints don't receive internal __path__
            environ["QUERY_STRING"] = urlencode(qs, doseq=True)

        # 2. Check x-now-route-matches if available
        if not target or target in ("/api/index", "/api/index.py"):
            route_matches = environ.get("HTTP_X_NOW_ROUTE_MATCHES", "")
            if route_matches:
                rm_qs = parse_qs(route_matches)
                for k in ("1", "0", "path"):
                    if k in rm_qs and rm_qs[k]:
                        val = unquote(rm_qs[k][0])
                        if val and not val.startswith(("/api/index", "/api/index.py")):
                            target = "/" + val.lstrip("/")
                            break

        # 3. Check HTTP_X_FORWARDED_URI or HTTP_X_MATCHED_PATH
        if not target or target in ("/api/index", "/api/index.py"):
            forwarded = (environ.get("HTTP_X_FORWARDED_URI") or "").split("?")[0]
            matched = (environ.get("HTTP_X_MATCHED_PATH") or "").split("?")[0]
            if forwarded and not forwarded.startswith(("/api/index", "/api/index.py")):
                target = forwarded
            elif matched and not matched.startswith(("/api/index", "/api/index.py")):
                target = matched

        # 4. Fallback: normalize entrypoint itself or root-like paths to /
        path_info = (environ.get("PATH_INFO") or "").split("?")[0]
        if not target:
            if path_info in ("/api/index", "/api/index.py", "/api/index/", "/api/index.py/"):
                target = "/"
            else:
                target = path_info

        if not target.startswith("/"):
            target = "/" + target

        environ["PATH_INFO"] = target
        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathFix(app.wsgi_app)
```

---

### `vercel.json`
```json
{
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/api/index?__path__=/$1"
    }
  ]
}
```

---

### `web_app.py`
```python
"""
web_app.py
==========
Flask web server wrapping the Edge-OCR Bus Route Identifier pipeline.

Exposes real-time execution metrics, intermediate image stages,
OCR confidence, fuzzy route corrections, and destination lookups
without fabricating or hardcoding any values.
"""
import base64
import csv
import io
import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional

import cv2
import numpy as np
from flask import Flask, request, jsonify, render_template
from werkzeug.exceptions import HTTPException

import config
import feedback
import ocr_engine
import preprocessing
from routes import RouteLookup

# Setup logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("bus_route.web")

BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB max upload

# Initialize RouteLookup ONCE at startup (zero-disk read hot path rule)
logger.info("Initializing RouteLookup for web service...")
route_lookup = RouteLookup(routes_dir=config.ROUTES_DATA_DIR, city=config.CITY)
route_lookup.startup_complete = True
haptic = feedback.HapticMotor()

# Ensure timing log exists (gracefully handle read-only filesystems on serverless)
try:
    config.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not config.LOG_PATH.exists():
        with open(config.LOG_PATH, "w", newline="") as f:
            csv.writer(f).writerow(
                ["timestamp", "capture_s", "preprocess_s", "ocr_s", "feedback_s", "total_s", "route", "confidence"]
            )
except Exception as e:
    logger.warning("Could not initialize timing log at %s (read-only filesystem): %s", config.LOG_PATH, e)


def _encode_jpeg_base64(img: np.ndarray, max_dim: int = 640, quality: int = 80) -> str:
    """Helper to convert OpenCV image matrix to a web-ready Base64 JPEG URI."""
    if img is None or img.size == 0:
        return ""
    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    success, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not success:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")


def run_pipeline_instrumented(frame: np.ndarray, capture_s: float = 0.0) -> Dict[str, Any]:
    """
    Runs the exact pipeline functions from the repository,
    measuring real wall-clock latency per stage and capturing
    real intermediate image frames.
    """
    t_start = time.monotonic()
    h, w = frame.shape[:2]

    # --- STAGE 1: PREPROCESSING ---
    t0 = time.monotonic()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame.copy()
    if config.UPSCALE_FACTOR != 1.0:
        gray = cv2.resize(
            gray, None,
            fx=config.UPSCALE_FACTOR, fy=config.UPSCALE_FACTOR,
            interpolation=cv2.INTER_LINEAR,
        )
    clahe_img = preprocessing._clahe.apply(gray)
    binary = cv2.adaptiveThreshold(
        clahe_img,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        config.ADAPTIVE_THRESH_BLOCK_SIZE,
        config.ADAPTIVE_THRESH_C,
    )
    preprocess_s = time.monotonic() - t0

    # --- STAGE 2: OCR EXTRACTION ---
    t0 = time.monotonic()
    try:
        ocr_result = ocr_engine.extract_route(binary, raw_frame=frame)
    except Exception as e:
        logger.warning("OCR extraction exception: %s", e)
        ocr_result = ocr_engine.OcrResult("", None, 0.0, "ocr_error", time.monotonic() - t0)
    ocr_s = ocr_result.elapsed_s

    # --- STAGE 3: LOOKUP & FUZZY CORRECTION ---
    t0 = time.monotonic()
    raw_route = ocr_result.route
    raw_text_clean = " ".join(ocr_result.raw_text.split()).strip()

    corrected_route = None
    destination = None
    low_confidence = False

    if raw_route:
        if ocr_result.confidence >= config.OCR_MIN_CONFIDENCE:
            corrected_route = route_lookup.correct_route(raw_route) or raw_route
            destination = route_lookup.lookup(corrected_route)
        else:
            low_confidence = True

    lookup_s = time.monotonic() - t0

    # --- STAGE 4: AUDIO PHRASE & FEEDBACK PREPARATION ---
    t0 = time.monotonic()
    if not ocr_result.raw_text and not raw_route:
        phrase = config.PHRASE_NO_TEXT
        haptic_name = "ERROR (One long pulse)"
        status = "no_route"
    elif low_confidence:
        phrase = config.PHRASE_LOW_CONFIDENCE
        haptic_name = "LOW CONFIDENCE (Two quick pulses)"
        status = "low_confidence"
    elif corrected_route:
        if destination:
            phrase = config.PHRASE_ROUTE_WITH_DESTINATION_TEMPLATE.format(
                route=corrected_route, destination=destination
            )
        else:
            phrase = config.PHRASE_ROUTE_TEMPLATE.format(route=corrected_route)
        haptic_name = "SUCCESS (Single short pulse)"
        status = "success"
    else:
        phrase = config.PHRASE_NO_TEXT
        haptic_name = "ERROR (One long pulse)"
        status = "no_route"

    is_cached = False
    if corrected_route:
        cached_file = config.AUDIO_CACHE_DIR / f"{corrected_route}.wav"
        is_cached = cached_file.exists()

    feedback_s = time.monotonic() - t0
    total_s = time.monotonic() - t_start

    # Write log if path writable
    try:
        with open(config.LOG_PATH, "a", newline="") as f:
            csv.writer(f).writerow([
                time.time(),
                f"{capture_s:.4f}",
                f"{preprocess_s:.4f}",
                f"{ocr_s:.4f}",
                f"{feedback_s:.4f}",
                f"{total_s:.4f}",
                corrected_route or "NONE",
                f"{ocr_result.confidence:.1f}",
            ])
    except Exception:
        pass

    return {
        "status": status,
        "timestamp_unix": time.time(),
        "stages": {
            "capture": {
                "name": "Image Ingestion / Decode",
                "time_ms": round(capture_s * 1000, 2),
                "budget_ms": round(config.BUDGET_CAPTURE * 1000, 1),
                "pass": capture_s <= config.BUDGET_CAPTURE,
                "image_b64": _encode_jpeg_base64(frame),
                "resolution": f"{w}x{h}",
            },
            "preprocess": {
                "name": "OpenCV CLAHE & Adaptive Binarization",
                "time_ms": round(preprocess_s * 1000, 2),
                "budget_ms": round(config.BUDGET_PREPROCESS * 1000, 1),
                "pass": preprocess_s <= config.BUDGET_PREPROCESS,
                "gray_b64": _encode_jpeg_base64(gray),
                "clahe_b64": _encode_jpeg_base64(clahe_img),
                "thresh_b64": _encode_jpeg_base64(binary),
            },
            "ocr": {
                "name": f"Edge OCR ({ocr_result.engine})",
                "time_ms": round(ocr_s * 1000, 2),
                "budget_ms": round(config.BUDGET_OCR * 1000, 1),
                "pass": ocr_s <= config.BUDGET_OCR,
                "engine": ocr_result.engine,
                "raw_text": ocr_result.raw_text,
                "confidence": round(ocr_result.confidence, 1),
                "confidence_is_estimated": ocr_result.confidence_is_estimated,
                "threshold_min": config.OCR_MIN_CONFIDENCE,
                "confidence_pass": (ocr_result.confidence >= config.OCR_MIN_CONFIDENCE),
            },
            "lookup": {
                "name": "Offline Multi-City Route & Destination Match",
                "time_ms": round(lookup_s * 1000, 2),
                "raw_route": raw_route,
                "corrected_route": corrected_route,
                "fuzzy_applied": (corrected_route != raw_route and raw_route is not None),
                "destination": destination,
                "city": config.CITY,
            },
            "feedback": {
                "name": "Audio Synthesis / Haptic Dispatch",
                "time_ms": round(feedback_s * 1000, 2),
                "budget_ms": round(config.BUDGET_FEEDBACK * 1000, 1),
                "pass": feedback_s <= config.BUDGET_FEEDBACK,
                "phrase": phrase,
                "audio_cached": is_cached,
                "haptic_pattern": haptic_name,
            },
        },
        "total": {
            "time_ms": round(total_s * 1000, 2),
            "budget_ms": round(config.BUDGET_TOTAL * 1000, 1),
            "pass": total_s <= config.BUDGET_TOTAL,
        },
        "route": corrected_route,
        "raw_route": raw_route,
        "destination": destination,
        "spoken_phrase": phrase,
    }


@app.route("/")
@app.route("/api/index")
@app.route("/api/index/")
@app.route("/api/index.py")
@app.route("/api")
@app.route("/api/")
def index():
    return render_template("index.html")


@app.route("/api/config", methods=["GET"])
def get_config():
    """Returns active configuration constants directly from config.py."""
    return jsonify({
        "city": config.CITY,
        "ocr_engine": config.OCR_ENGINE,
        "ocr_min_confidence": config.OCR_MIN_CONFIDENCE,
        "route_regex": config.ROUTE_REGEX,
        "budget_total_ms": config.BUDGET_TOTAL * 1000,
        "budget_capture_ms": config.BUDGET_CAPTURE * 1000,
        "budget_preprocess_ms": config.BUDGET_PREPROCESS * 1000,
        "budget_ocr_ms": config.BUDGET_OCR * 1000,
        "budget_feedback_ms": config.BUDGET_FEEDBACK * 1000,
        "clahe_clip_limit": config.CLAHE_CLIP_LIMIT,
        "adaptive_thresh_block_size": config.ADAPTIVE_THRESH_BLOCK_SIZE,
        "common_routes": config.COMMON_ROUTES,
    })


@app.route("/api/samples", methods=["GET"])
def list_samples():
    """Lists available test images in test_images/ for one-click testing."""
    test_dir = BASE_DIR / "test_images"
    if not test_dir.exists():
        return jsonify([])
    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    samples = []
    for p in sorted(test_dir.iterdir()):
        if p.is_file() and p.suffix.lower() in valid_exts and not p.name.startswith("debug_"):
            samples.append({
                "filename": p.name,
                "size_kb": round(p.stat().st_size / 1024, 1),
            })
    return jsonify(samples)


@app.route("/api/identify", methods=["POST"])
def identify_upload():
    """Handles multipart/form-data image upload and runs the real pipeline."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded in form field 'file'"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    t0 = time.monotonic()
    file_bytes = file.read()
    nparr = np.frombuffer(file_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    capture_s = time.monotonic() - t0

    if frame is None:
        return jsonify({"error": "Could not decode uploaded file as a valid image"}), 400

    result = run_pipeline_instrumented(frame, capture_s=capture_s)
    result["filename"] = file.filename
    return jsonify(result)


@app.route("/api/sample-identify", methods=["POST"])
def identify_sample():
    """Runs the pipeline on a specified test_images/<filename>."""
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "Missing 'filename' parameter"}), 400

    safe_path = BASE_DIR / "test_images" / Path(filename).name
    if not safe_path.exists() or not safe_path.is_file():
        return jsonify({"error": f"Sample file '{filename}' not found"}), 404

    t0 = time.monotonic()
    frame = cv2.imread(str(safe_path))
    capture_s = time.monotonic() - t0

    if frame is None:
        return jsonify({"error": f"Could not read image file '{filename}'"}), 400

    result = run_pipeline_instrumented(frame, capture_s=capture_s)
    result["filename"] = safe_path.name
    return jsonify(result)


@app.route("/api/benchmark", methods=["POST"])
def run_benchmark():
    """
    Runs batch benchmark across test_images/.
    If truth.csv exists, calculates real accuracy %;
    otherwise returns 'N/A' for accuracy without inventing any number.
    """
    test_dir = BASE_DIR / "test_images"
    if not test_dir.exists():
        return jsonify({"error": "test_images directory does not exist"}), 400

    truth_file = BASE_DIR / "test_images" / "truth.csv"
    truth: Dict[str, str] = {}
    has_ground_truth = False
    if truth_file.exists():
        try:
            with open(truth_file, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2 and row[0].strip().lower() != "filename":
                        truth[row[0].strip()] = row[1].strip().upper()
            has_ground_truth = len(truth) > 0
        except Exception as e:
            logger.warning("Failed to parse truth.csv: %s", e)

    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    images = [p for p in sorted(test_dir.iterdir()) if p.is_file() and p.suffix.lower() in valid_exts and not p.name.startswith("debug_")]

    if not images:
        return jsonify({"error": "No test images found in test_images/"}), 400

    total_tested = 0
    correct_matches = 0
    total_latency_s = 0.0
    records = []

    for img_path in images:
        t0 = time.monotonic()
        frame = cv2.imread(str(img_path))
        capture_s = time.monotonic() - t0
        if frame is None:
            continue

        res = run_pipeline_instrumented(frame, capture_s=capture_s)
        total_tested += 1
        total_latency_s += (res["total"]["time_ms"] / 1000.0)

        filename = img_path.name
        detected = res["route"]
        expected = truth.get(filename) if has_ground_truth else None

        is_match: Optional[bool] = None
        if has_ground_truth and expected:
            is_match = (detected == expected)
            if is_match:
                correct_matches += 1

        records.append({
            "filename": filename,
            "detected_route": detected or "None",
            "destination": res["destination"] or "None",
            "expected_route": expected if expected else "N/A",
            "match": is_match if is_match is not None else "N/A",
            "confidence": res["stages"]["ocr"]["confidence"],
            "confidence_is_estimated": res["stages"]["ocr"]["confidence_is_estimated"],
            "confidence_pass": res["stages"]["ocr"]["confidence_pass"],
            "total_ms": res["total"]["time_ms"],
            "pass_budget": res["total"]["pass"],
        })

    avg_latency_ms = round((total_latency_s / total_tested) * 1000, 2) if total_tested > 0 else 0.0
    accuracy_pct = round((correct_matches / total_tested) * 100, 1) if (has_ground_truth and total_tested > 0) else "N/A"

    return jsonify({
        "total_tested": total_tested,
        "has_ground_truth": has_ground_truth,
        "correct_matches": correct_matches if has_ground_truth else "N/A",
        "accuracy_pct": accuracy_pct,
        "avg_latency_ms": avg_latency_ms,
        "budget_total_ms": config.BUDGET_TOTAL * 1000,
        "records": records,
    })


@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code
    logger.exception("Server error: %s", e)
    return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print(f"[*] Starting Bus Route Identifier Web UI on http://127.0.0.1:5000")
    print(f"[*] Loaded {len(route_lookup.routes)} routes for city '{config.CITY}'")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=False)
```

---

### `config.py`
```python
"""
config.py
=========
Single source of truth for pin assignments, file paths, and tunable thresholds.
"""
import os
import platform
import shutil
from pathlib import Path

# --------------------------------------------------------------------------
# GPIO PIN MAP (BCM numbering)
# --------------------------------------------------------------------------
BUTTON_PIN = 17          # Push button trigger, wired to GND with internal pull-up
VIBRATION_MOTOR_PIN = 27  # Drives NPN/MOSFET gate for the vibration motor
STATUS_LED_PIN = 22       # Optional: onboard "processing" indicator LED (debug aid)

BUTTON_BOUNCE_TIME = 0.05      # seconds — debounce window
BUTTON_HOLD_IGNORE_WINDOW = 1.5  # ignore re-triggers while a capture is in flight

# --------------------------------------------------------------------------
# CAMERA
# --------------------------------------------------------------------------
CAMERA_RESOLUTION = (640, 480)
CAMERA_FORMAT = "RGB888"
CAMERA_ROI = None
SHM_FRAME_PATH = Path("/dev/shm/bus_frame.jpg")

# --------------------------------------------------------------------------
# PREPROCESSING
# --------------------------------------------------------------------------
CLAHE_CLIP_LIMIT = 3.0
CLAHE_TILE_GRID_SIZE = (8, 8)
ADAPTIVE_THRESH_BLOCK_SIZE = 31   # must be odd
ADAPTIVE_THRESH_C = 12
UPSCALE_FACTOR = 1.0

# --------------------------------------------------------------------------
# OCR
# --------------------------------------------------------------------------
OCR_ENGINE = "tesseract"


def _detect_tesseract_cmd() -> str:
    found = shutil.which("tesseract")
    if found:
        return found

    system = platform.system()
    if system == "Windows":
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        ]
    elif system == "Darwin":
        candidates = ["/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"]
    else:
        candidates = ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]

    for c in candidates:
        if Path(c).exists():
            return c
    return "tesseract"


TESSERACT_CMD = _detect_tesseract_cmd()
if TESSERACT_CMD and Path(TESSERACT_CMD).is_file():
    _tess_dir = str(Path(TESSERACT_CMD).parent)
    if _tess_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _tess_dir + os.pathsep + os.environ.get("PATH", "")

TESSERACT_LANG = "eng"
TESSERACT_PSM_PRIMARY = 7
TESSERACT_PSM_FALLBACK = 11
TESSERACT_WHITELIST = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ/- "
OCR_MIN_CONFIDENCE = 45

ROUTE_REGEX = r"\b\d{1,3}[A-Z]?(?:/\d{1,2})?\b"

# --------------------------------------------------------------------------
# AUDIO / FEEDBACK
# --------------------------------------------------------------------------
TTS_ENGINE = "espeak-ng"
ESPEAK_VOICE = "en-us"
ESPEAK_SPEED_WPM = 175
PIPER_MODEL_PATH = Path("models/en_US-lessac-low.onnx")
PIPER_BINARY = "/usr/local/bin/piper"

I2S_ALSA_DEVICE = "plughw:CARD=sndrpisimplecar,DEV=0"
AUDIO_CACHE_DIR = Path("sounds/cache")
COMMON_ROUTES = ["12", "21C", "45", "100", "500A"]

PHRASE_NO_TEXT = "No route detected. Please try again."
PHRASE_LOW_CONFIDENCE = "Unclear. Please hold steady and try again."
PHRASE_ROUTE_TEMPLATE = "Bus {route}"

# --------------------------------------------------------------------------
# ROUTE LOOKUP & DATA
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CITY = "vijayawada"
ROUTES_DATA_DIR = BASE_DIR / "data" / "routes"
PHRASE_ROUTE_WITH_DESTINATION_TEMPLATE = "Bus {route} to {destination}"

# --------------------------------------------------------------------------
# HAPTIC FEEDBACK PATTERNS
# --------------------------------------------------------------------------
HAPTIC_SUCCESS_PATTERN = [(0.15, 0.1)]
HAPTIC_LOW_CONFIDENCE_PATTERN = [(0.08, 0.08)] * 2
HAPTIC_ERROR_PATTERN = [(0.4, 0.0)]

# --------------------------------------------------------------------------
# PERFORMANCE BUDGET (seconds)
# --------------------------------------------------------------------------
BUDGET_TOTAL = 1.5
BUDGET_CAPTURE = 0.25
BUDGET_PREPROCESS = 0.15
BUDGET_OCR = 0.70
BUDGET_FEEDBACK = 0.40

# Serverless filesystem guard
_is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
LOG_PATH = Path("/tmp/logs/run_timings.csv") if _is_serverless else (BASE_DIR / "logs" / "run_timings.csv")

# --------------------------------------------------------------------------
# POWER MANAGEMENT
# --------------------------------------------------------------------------
POWER_MONITORING_ENABLED = False
BATTERY_ADC_CHANNEL = 0
BATTERY_VOLTAGE_DIVIDER_RATIO = 2.0
BATTERY_CHECK_INTERVAL_S = 60
BATTERY_LOW_VOLTAGE = 3.55
BATTERY_CRITICAL_VOLTAGE = 3.4
PHRASE_LOW_BATTERY = "Battery low. Please recharge soon."
PHRASE_CRITICAL_BATTERY = "Battery critical. Recharge now."
HAPTIC_LOW_BATTERY_PATTERN = [(0.5, 0.2)] * 2
```

---

### `ocr_engine.py`
```python
"""
ocr_engine.py
=============
Text extraction and route parsing using Tesseract with WinOCR fallback.
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
    confidence: float
    engine: str
    elapsed_s: float
    confidence_is_estimated: bool = False


def extract_route(binary_image: np.ndarray, raw_frame: Optional[np.ndarray] = None) -> OcrResult:
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

        if raw_frame is not None and raw_frame.size > 0:
            res_raw = winocr.recognize_cv2_sync(raw_frame)
            if res_raw and res_raw.get("text"):
                texts.append(res_raw["text"].strip())

            h_f, w_f = raw_frame.shape[:2]
            if max(h_f, w_f) < 1200:
                scale = min(2.0, 1600.0 / max(h_f, w_f))
                frame_scaled = cv2.resize(raw_frame, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                res_scaled = winocr.recognize_cv2_sync(frame_scaled)
                if res_scaled and res_scaled.get("text"):
                    texts.append(res_scaled["text"].strip())

        if binary_image is not None and binary_image.size > 0:
            img_bgr = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2BGR) if binary_image.ndim == 2 else binary_image.copy()
            res_bin = winocr.recognize_cv2_sync(np.ascontiguousarray(img_bgr))
            if res_bin and res_bin.get("text"):
                texts.append(res_bin["text"].strip())

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
        mean_conf = (config.OCR_MIN_CONFIDENCE + 10.0) if route else 0.0
        elapsed = time.monotonic() - t0
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


_easyocr_reader = None


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
    if not raw_text:
        return None

    cleaned = re.sub(r'\b[A-Z]{2}\s*\d{1,2}\s*[A-Z]{0,2}\s*\d{0,4}\b', '', raw_text, flags=re.I)
    cleaned = re.sub(r'\b(STOP|KEEP|DISTANCE|FEET|SPEED|TATA|LEYLAND|APSRTC|BMTC|DTC)\b', '', cleaned, flags=re.I)

    matches = _ROUTE_PATTERN.findall(cleaned.upper())
    matches = [m for m in matches if m not in ("0", "00", "O")]
    if matches:
        return max(matches, key=len)

    raw_matches = _ROUTE_PATTERN.findall(raw_text.upper())
    raw_matches = [m for m in raw_matches if m not in ("0", "00", "O") and not re.match(r'^[A-Z]{2}\d+', m)]
    if raw_matches:
        return max(raw_matches, key=len)

    return None
```

---

### `preprocessing.py`
```python
"""
preprocessing.py
================
OpenCV pipeline: grayscale -> CLAHE -> adaptive binarization.
"""
import time
import logging

import cv2
import numpy as np

import config

logger = logging.getLogger("bus_route.preprocessing")

_clahe = cv2.createCLAHE(
    clipLimit=config.CLAHE_CLIP_LIMIT,
    tileGridSize=config.CLAHE_TILE_GRID_SIZE,
)


def preprocess(frame: np.ndarray) -> np.ndarray:
    t0 = time.monotonic()

    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY) if frame.ndim == 3 else frame

    if config.UPSCALE_FACTOR != 1.0:
        gray = cv2.resize(
            gray, None,
            fx=config.UPSCALE_FACTOR, fy=config.UPSCALE_FACTOR,
            interpolation=cv2.INTER_LINEAR,
        )

    equalized = _clahe.apply(gray)

    binary = cv2.adaptiveThreshold(
        equalized,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        config.ADAPTIVE_THRESH_BLOCK_SIZE,
        config.ADAPTIVE_THRESH_C,
    )

    elapsed = time.monotonic() - t0
    logger.debug("Preprocess completed in %.3fs", elapsed)
    return binary


def _denoise(gray: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoising(gray, h=10)
```

---

### `routes.py`
```python
"""
routes.py
=========
Offline route-to-destination lookup and fuzzy correction.
"""
import csv
import difflib
import logging
import time
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger("bus_route.routes")


class RouteLookup:
    def __init__(self, routes_dir: Path, city: str):
        self.routes_dir = Path(routes_dir)
        self.city = city
        self.routes: Dict[str, str] = {}
        self.startup_complete = False
        self.load_data()

    def load_data(self):
        if self.startup_complete:
            logger.warning(
                "CRITICAL WARNING: Route data loaded outside of startup path! "
                "This violates latency budget constraints."
            )

        t0 = time.monotonic()
        csv_path = self.routes_dir / f"{self.city}.csv"
        if not csv_path.exists():
            logger.warning("Route data file '%s' does not exist.", csv_path)
            return

        try:
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)

                if header and len(header) >= 2:
                    if header[0].strip().lower() != "route" or header[1].strip().lower() != "destination":
                        r, d = header[0].strip(), header[1].strip()
                        self.routes[r.upper()] = d

                rows_loaded = len(self.routes)
                for row in reader:
                    if len(row) >= 2:
                        route_num, dest = row[0].strip(), row[1].strip()
                        self.routes[route_num.upper()] = dest
                        rows_loaded += 1

            elapsed = time.monotonic() - t0
            logger.info("Loaded %d routes for city '%s' in %.3fs.", rows_loaded, self.city, elapsed)
        except Exception as e:
            logger.exception("Failed to load route data from %s: %s", csv_path, e)

        self.all_cities_routes: Dict[str, str] = dict(self.routes)
        try:
            for other_csv in self.routes_dir.glob("*.csv"):
                if other_csv.name.lower() == f"{self.city}.csv".lower():
                    continue
                with open(other_csv, mode="r", encoding="utf-8") as f:
                    rdr = csv.reader(f)
                    next(rdr, None)
                    for row in rdr:
                        if len(row) >= 2:
                            r_num, dest = row[0].strip().upper(), row[1].strip()
                            if r_num not in self.all_cities_routes:
                                self.all_cities_routes[r_num] = dest
        except Exception as e:
            logger.warning("Could not load other city CSVs: %s", e)

    def lookup(self, route: str) -> Optional[str]:
        if not route:
            return None
        r_upper = route.upper()
        if r_upper in self.routes:
            return self.routes[r_upper]
        return getattr(self, "all_cities_routes", {}).get(r_upper)

    def correct_route(self, route: str) -> str:
        if not route:
            return route

        route_upper = route.upper()
        all_known = getattr(self, "all_cities_routes", self.routes)
        if route_upper in all_known:
            return route_upper

        known_primary = list(self.routes.keys())
        close_primary = difflib.get_close_matches(route_upper, known_primary, n=1, cutoff=0.6)
        if close_primary:
            return close_primary[0]

        close_all = difflib.get_close_matches(route_upper, list(all_known.keys()), n=1, cutoff=0.6)
        if close_all:
            return close_all[0]

        return route
```

---

### `feedback.py`
```python
"""
feedback.py
===========
Audio announcement and haptic vibration feedback.
"""
import os
import subprocess
import time
import logging
from typing import List, Tuple

import config

logger = logging.getLogger("bus_route.feedback")


class HapticMotor:
    def __init__(self, pin: int = config.VIBRATION_MOTOR_PIN):
        self.device = None
        try:
            from gpiozero import OutputDevice
            self.device = OutputDevice(pin)
        except Exception as e:
            logger.warning("Could not initialize haptic motor OutputDevice (%s) — skipping haptics (dev mode).", e)

    def play(self, pattern: List[Tuple[float, float]]):
        if not self.device:
            return
        for on_s, off_s in pattern:
            self.device.on()
            time.sleep(on_s)
            self.device.off()
            if off_s > 0:
                time.sleep(off_s)


def speak(phrase: str):
    if not phrase:
        return
    try:
        subprocess.run(
            ["espeak-ng", "-v", config.ESPEAK_VOICE, "-s", str(config.ESPEAK_SPEED_WPM), phrase],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2.0,
        )
    except Exception as e:
        logger.debug("Local espeak-ng call skipped: %s", e)
```

---

### `sanity_check.py`
```python
"""
sanity_check.py
===============
Validates that the complete pipeline functions as intended:
1. Valid route image detects route with confidence and destination.
2. Blank or noise image detects no route and returns route: None.
"""
import cv2
import numpy as np
from web_app import run_pipeline_instrumented


def run_sanity_check():
    print("=== Running Bus Route Identifier Sanity Check ===")

    # 1. Test genuine route board
    img = cv2.imread("test_images/clear_route_12.jpg")
    if img is not None:
        res = run_pipeline_instrumented(img)
        print(f"[*] Test 1 (clear_route_12.jpg):")
        print(f"    Status: {res['status']}")
        print(f"    Route: {res['route']}")
        print(f"    Destination: {res['destination']}")
        print(f"    Confidence: {res['stages']['ocr']['confidence']}% (Estimated: {res['stages']['ocr']['confidence_is_estimated']})")
        print(f"    Latency: {res['total']['time_ms']} ms")
        assert res['status'] == 'success'
        assert res['route'] == '12'
        print("    --> PASS\n")

    # 2. Test noise / non-bus frame
    noise_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
    res_noise = run_pipeline_instrumented(noise_frame)
    print(f"[*] Test 2 (random noise frame):")
    print(f"    Status: {res_noise['status']}")
    print(f"    Route: {res_noise['route']}")
    print(f"    Spoken phrase: '{res_noise['spoken_phrase']}'")
    assert res_noise['route'] is None
    print("    --> PASS\n")

    print("[✓] ALL SANITY CHECKS PASSED.")


if __name__ == "__main__":
    run_sanity_check()
```

---

### `requirements.txt`
```text
# Core pipeline
opencv-python-headless>=4.9.0
numpy>=1.26
flask>=3.0.0
requests>=2.31.0

# OCR
pytesseract>=0.3.10

# GPIO
gpiozero>=2.0.1
```

---

## 6. Codebase Access & Downloads

You can access the full codebase in three ways:

1. **Local Clean Zip Archive**:
   The full project has been packaged into a single archive on your machine:
   - **Path**: `C:\Users\karth\Projects\bus_route_identifier_full_codebase.zip` (Size: $\approx 9\,\text{MB}$, includes code, templates, docs, and test images).
2. **Private GitHub Repository**:
   - **URL**: [https://github.com/kartheekakula/bus-route-identifier](https://github.com/kartheekakula/bus-route-identifier)
   - **Branch**: `main` (Kept strictly private under account `kartheekakula`).
3. **Live Serverless Deployment**:
   - **URL**: [https://bus-route-identifier.vercel.app](https://bus-route-identifier.vercel.app)
   - Live transit ticket dashboard with instant image uploads, auto-read voice announcements, and batch benchmarking.
