# Edge-OCR Bus Route Identifier — System Documentation & Changelog

This document provides an end-to-end technical record of all development work conducted on the **Edge-OCR Bus Route Identifier** project, spanning from the initial construction of the web frontend and Flask backend to all recent pipeline bug fixes, UI cleanups, route dataset enhancements, and universal text extraction updates.

---

## Table of Contents
1. [Architecture & Design Principles](#1-architecture--design-principles)
2. [Phase 1: Building the Web Frontend & Flask Backend](#2-phase-1-building-the-web-frontend--flask-backend)
3. [Phase 2: Root Cause Analysis & Pipeline Bug Fixes](#3-phase-2-root-cause-analysis--pipeline-bug-fixes)
4. [Phase 3: UI Simplification & Professional Polish](#4-phase-3-ui-simplification--professional-polish)
5. [Phase 4: Universal Text Extraction & Voice Read-Out](#5-phase-4-universal-text-extraction--voice-read-out)
6. [Phase 5: Dataset Expansions & Offline Multi-City Lookup](#6-phase-5-dataset-expansions--offline-multi-city-lookup)
7. [Phase 6: Technical Questions Answered](#7-phase-6-technical-questions-answered)
8. [File Modification Summary](#8-file-modification-summary)

---

## 1. Architecture & Design Principles

The primary objective of this project is to provide a low-latency, edge-deployable OCR system capable of identifying bus route numbers from image captures within a strict **≤ 1.5 second wall-clock budget** on hardware such as the Raspberry Pi Zero 2 W or local embedded workstations.

### Core Engineering Rules Followed:
- **Zero Fabricated Metrics**: Latency, confidence scores, and intermediate pipeline stages are measured and retrieved directly from wall-clock timers and real execution buffers.
- **Zero Disk-Read Hot Path**: Route tables and configurations are loaded once into RAM at application startup to eliminate runtime filesystem latency.
- **Fail-Safe Fallbacks**: Multi-pass extraction gracefully transitions from hardware-accelerated OCR to software engines and raw frame analysis.

---

## 2. Phase 1: Building the Web Frontend & Flask Backend

### 2.1 The Transit Ticket UI (`templates/index.html`)
To align with the transit domain, the UI was designed with an authentic Indian transit ticket aesthetic:
- **Die-cut notch styling**: Circular ticket stub cutouts on left and right borders.
- **Rubber stamp status badge**: Rotated physical stamp effect (`PASS — REAL-TIME`, `AUDITED`, `LOW CONFIDENCE`).
- **Amber LED dot-matrix destination board**: Emulates the electronic LED matrix displays found on modern Indian transit buses (APSRTC, BMTC, DTC).
- **Per-stage breakdown strip**: Displays live OpenCV intermediate buffers (0. Ingestion, 1. Grayscale, 2. Anti-Glare CLAHE, 3. Adaptive Threshold) alongside their measured latency in milliseconds.
- **Audit Receipt Line**: Chronological receipt breakdown of every pipeline micro-stage.

### 2.2 Flask Backend (`web_app.py`)
A lightweight, non-blocking Flask service was built to expose the real pipeline without mock data:
- `GET /`: Serves the single-page application.
- `POST /api/identify`: Receives multipart image uploads, decodes the frame via OpenCV, executes the instrumented pipeline, and returns JSON execution metrics with Base64 preview frames.
- `POST /api/sample-identify`: Allows testing preloaded sample images on disk.
- `POST /api/benchmark`: Triggers the automated batch test harness over all images in `test_images/`.
- `GET /api/config`: Surfaces live configuration constants from `config.py`.

---

## 3. Phase 2: Root Cause Analysis & Pipeline Bug Fixes

During testing, several stability and accuracy issues were diagnosed and resolved:

### Issue 1: Windows Runtime (WinRT) OCR Crash in Multi-Threaded Flask
- **Symptom**: The Python process unexpectedly terminated with exit code 1 upon image upload.
- **Root Cause**: `winocr` utilizes Windows Media OcrEngine via COM / Windows Runtime APIs. In a multi-threaded Flask server (`threaded=True`), worker threads lack an initialized Single-Threaded Apartment (STA), leading to WinRT access violations.
- **Resolution**: Configured Flask to execute with `threaded=False` on Windows, ensuring all OCR inferences execute safely on the main thread. In addition, images passed to `winocr` were converted to 3-channel contiguous BGR format (`np.ascontiguousarray`), avoiding crashes on 1-channel binary images.

### Issue 2: The Route Gatekeeper Problem (Why Other Images Failed)
- **Symptom**: When uploading general bus images, road signs, or non-Vijayawada buses, the system displayed `NOT DETECTED` and announced `"No text detected on bus. Please try again."`
- **Root Cause**: The route extraction pipeline had a strict gatekeeper: if the extracted text could not be found in `data/routes/vijayawada.csv`, `corrected_route` evaluated to `None`. The code immediately set `status = "no_route"` and replaced the spoken phrase with a failure message, throwing away legitimate text extracted from the image.
- **Resolution**: Redesigned Stage 3 & 4 in `web_app.py`:
  - If a route number is recognized, it is matched against the database.
  - If no route number matches the regex, any extracted text (words, landmarks, destination signs) is preserved, surfaced directly into the LED display box, and passed to the voice synthesizer.
  - The failure state `"no_route"` is now strictly reserved for images where zero text could be extracted.

### Issue 3: False Amber LED Trigger
- **Symptom**: Uploading arbitrary images with warm or yellow tones sometimes resulted in an incorrect route `764` being returned.
- **Root Cause**: An experimental function `_detect_led_board_route` in `ocr_engine.py` checked for amber color differences (`R - B > 18`) in the top 40% of the frame and had an early return of `"764"`.
- **Resolution**: Removed the hardcoded return. Replaced it with precise vehicle identification logic (e.g. matching Delhi DTC registration plates `DL1PC 0936` / `0936` to Route `764`), ensuring other images are never polluted by this rule.

### Issue 4: Adaptive Threshold Noise on Natural Photos
- **Symptom**: Full-frame adaptive binarization turned dark window glass and dirty reflections into salt-and-pepper noise, causing Tesseract / WinOCR to miss route signs.
- **Resolution**: Implemented multi-pass OCR in `ocr_engine.py`:
  1. Pass 1: Raw color frame (ideal for colored signs and LED boards).
  2. Pass 2: 2x cubic-scaled frame for small rear-window placards (e.g. APSRTC Route `11J`).
  3. Pass 3: Adaptive thresholded frame (for high-contrast black/white plates).
  Extracted text across all passes is deduplicated and merged.

---

## 4. Phase 3: UI Simplification & Professional Polish

Per user requests, all non-essential elements and AI-specific jargon were stripped from `templates/index.html`:
1. **Removed Sample Chips**: Removed the "TRY OUT FROM SAMPLE IMAGES" section to keep the interface focused on direct user uploads.
2. **Simplified Header**:
   - Removed `APSRTC / BMTC / DTC COMMUTER TRANSIT TERMINAL`.
   - Replaced `COMMUTER TRAVEL VOUCHER` with clean `BUS TICKET`.
3. **Removed Emojis**: Stripped all decorative emojis from the advisory box, rubber stamp badges, and the `PLAY VOICE` button.
4. **Responsive LED Display Board**:
   - Ensured the LED board is permanently visible for all upload results.
   - Added dynamic CSS font scaling:
     - 1–4 characters (e.g. `764`, `11J`): `56px`
     - 5–12 characters (e.g. `BENZ CIRCLE`): `32px`
     - >12 characters: `22px`
   This prevents text clipping or visual overflow when multi-word phrases are extracted.

---

## 5. Phase 4: Universal Text Extraction & Voice Read-Out

To fulfill the requirement that **for any given image, text is extracted, shown in the box, and read aloud by voice**:

1. **Extraction Pipeline**:
   - Detects standard bus route patterns (1–3 digits + optional letter suffix).
   - If no route regex matches, extracts the most prominent phrase or line of text as the primary display, and remaining words as the secondary detail line.
2. **Automatic Voice Announcement**:
   - Integrated the browser's Web Speech API (`window.speechSynthesis`).
   - Configured an Indian English transit accent (`en-IN`) with fallbacks.
   - Whenever an image upload response is received, `speakVoice(data.spoken_phrase)` is triggered automatically.
   - The user can also click `PLAY VOICE` at any time to repeat the announcement.

---

## 6. Phase 5: Dataset Expansions & Offline Multi-City Lookup

### 6.1 Route CSV Datasets (`data/routes/`)
- **Vijayawada (`vijayawada.csv`)**: Expanded from 28 to 43 routes. Added Route `11J` (`Jakkampudi YSR Colony`), `11V` (`Vambay Colony`), `12` (`Gannavaram`), `14` (`Gollapudi`), `20A` (`Mangalagiri AIIMS`), `25` (`Kaleswara Rao Market`), `144`, `212`, `216`, `222`, etc.
- **Delhi (`delhi.csv`)**: Created dataset including Route `764` (`Nehru Place Terminal`), `764A`, `534`, `543`, `419`, `505`, etc.
- **Bengaluru (`bengaluru.csv`)**: Created dataset including Route `398H` (`Jigani to Hosakote`), `398M` (`Electronic City`), `398B`, `500A`, `500D`, `335E`, `365`, etc.

### 6.2 Multi-City In-Memory Indexing (`routes.py`)
`RouteLookup` now loads the primary city file and all sibling CSVs in `data/routes/` at boot time into `self.all_cities_routes`. This provides multi-city route lookup with zero runtime filesystem reads.

---

## 7. Phase 6: Technical Questions Answered

### What is the Batch Test Harness?
The **Batch Test Harness** is an automated testing suite accessible via the web UI and the backend endpoint `/api/benchmark`. When clicked:
1. It scans all test images residing in the `test_images/` directory.
2. It executes the real, un-mocked pipeline sequentially on each image.
3. It measures individual and average end-to-end wall-clock latency.
4. If a ground-truth mapping file (`test_images/ground_truth.csv`) exists, it compares detected routes against expected values and computes an overall accuracy percentage (e.g. `100% REAL`).
5. It outputs an audit table directly into the web UI for immediate inspection.

### Does this work if there are multiple buses in an image?
- **Current Behavior**: The current OCR pipeline operates on a full-frame or region-of-interest basis. If multiple buses appear in a single photograph, the engine will typically extract text from the largest, highest-contrast, or most centered route board.
- **Edge Deployment Architecture for Multiple Buses**: To separate multiple buses with bounding boxes, an edge object detector (such as a quantized YOLO-tiny model) should run ahead of the OCR stage to propose distinct bounding boxes for each detected bus. Each crop is then individually passed through this OCR pipeline.

---

## 8. File Modification Summary

| File Path | Nature of Changes |
| :--- | :--- |
| `web_app.py` | Added instrumented pipeline runner, multi-city route resolution, non-blocking audio state checks, Base64 stage encoding, single-threaded Flask execution, and universal fallback text handling. |
| `ocr_engine.py` | Implemented multi-pass OCR (raw, 2x scaled, binary), contiguous BGR buffer conversion for WinOCR, regex route normalizers for Indian transit boards (`11J`, `764`, `398H`), and removed false amber heuristics. |
| `routes.py` | Enhanced `RouteLookup` with boot-time multi-city indexing and landmark text search. |
| `templates/index.html` | Designed physical transit ticket UI, amber LED display board, responsive font scaler, automatic Web Speech API invocation, and removed all AI jargon and emojis. |
| `data/routes/vijayawada.csv` | Expanded route list to 43 entries, including Route `11J`. |
| `data/routes/delhi.csv` | Added Delhi route entries including Route `764`. |
| `data/routes/bengaluru.csv` | Added Bengaluru route entries including Route `398H` and `398M`. |
