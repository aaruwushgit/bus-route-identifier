"""
check_tesseract.py
===================
Run this directly (`python check_tesseract.py`) to find out exactly why
Tesseract isn't being used, with NO fallback and NO exception swallowing.
The main pipeline deliberately falls back to Windows OCR on any Tesseract
failure so a single bad frame doesn't crash a request — which is correct
for the app, but it also means the *real* error never reaches you. This
script exists to show you that real error, unfiltered.
"""
import shutil
import platform
import sys

import config

print("=" * 70)
print("TESSERACT DIAGNOSTIC")
print("=" * 70)

print(f"\nPlatform: {platform.system()} {platform.release()}")
print(f"config.TESSERACT_CMD resolved to: {config.TESSERACT_CMD!r}")
print(f"shutil.which('tesseract'): {shutil.which('tesseract')!r}")

from pathlib import Path
p = Path(config.TESSERACT_CMD)
print(f"Path exists: {p.exists()} (checked: {p})" if not shutil.which("tesseract") else "")

print("\n--- Attempting to import pytesseract and call the binary ---")
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    version = pytesseract.get_tesseract_version()
    print(f"SUCCESS: Tesseract version {version} responded correctly.")
    print("\nIf the web app is still showing 'winocr' as the engine, the issue")
    print("is happening at request time, not at startup — check the Flask")
    print("server's console output for an 'OCR ENGINE READY' or a red-flagged")
    print("'unexpected error' log line when you upload an image.")
except pytesseract.pytesseract.TesseractNotFoundError as e:
    print(f"\nFAILURE (TesseractNotFoundError): {e}")
    print("\nThis means the binary genuinely isn't at the resolved path above.")
    print("Fix: install Tesseract-OCR for Windows (UB-Mannheim build:")
    print("https://github.com/UB-Mannheim/tesseract/wiki), and either:")
    print("  (a) tick 'Add to PATH' during install, then restart your terminal, or")
    print(r"  (b) confirm it landed at C:\Program Files\Tesseract-OCR\tesseract.exe")
    print("      (config.py already checks that path automatically).")
except Exception as e:
    print(f"\nFAILURE ({type(e).__name__}): {e}")
    print("\nThis is NOT a 'not installed' error — the binary was found and ran,")
    print("but something else went wrong (e.g. missing eng.traineddata language")
    print("file, a permissions issue, or a corrupted install). Full traceback:")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n--- Running an actual OCR pass on a synthetic test image ---")
try:
    import cv2
    import numpy as np
    img = np.full((200, 500), 255, dtype=np.uint8)
    cv2.putText(img, "12", (60, 140), cv2.FONT_HERSHEY_SIMPLEX, 4, (0,), 8)
    text = pytesseract.image_to_string(img, config="--psm 7")
    print(f"OCR read back: {text.strip()!r}")
    if "12" in text:
        print("SUCCESS: Tesseract is fully working end to end on this machine.")
    else:
        print("Tesseract ran without error but didn't read the test text correctly.")
        print("That's a preprocessing/image-quality issue, not an install issue.")
except Exception as e:
    print(f"Unexpected failure during the OCR pass itself: {type(e).__name__}: {e}")
