import cv2
import numpy as np
import web_app

print("=== RUNNING PIPELINE SANITY CHECK ===")

# Test 1: Clear, valid route-board image (e.g. Route 12 - Gannavaram)
img_valid = np.full((300, 600, 3), 245, dtype=np.uint8)
cv2.rectangle(img_valid, (40, 40), (560, 260), (20, 20, 20), -1)  # dark destination board
cv2.putText(img_valid, "12", (80, 200), cv2.FONT_HERSHEY_SIMPLEX, 4.5, (255, 255, 255), 10) # crisp route text
cv2.putText(img_valid, "GANNAVARAM", (300, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 3)

out_valid = web_app.run_pipeline_instrumented(img_valid)
print("\n--- TEST 1: Clear, Valid Route Board (Route 12) ---")
print("status                   :", out_valid.get("status"))
print("route                    :", out_valid.get("route"))
print("destination              :", out_valid.get("destination"))
print("stages.ocr.engine        :", out_valid["stages"]["ocr"]["engine"])
print("stages.ocr.confidence    :", out_valid["stages"]["ocr"]["confidence"])
print("confidence_is_estimated :", out_valid["stages"]["ocr"]["confidence_is_estimated"])
print("spoken_phrase            :", out_valid.get("spoken_phrase"))

# Test 2: Blank / noisy image
img_blank = np.random.randint(50, 150, (300, 600, 3), dtype=np.uint8) # pure noise, no text
out_blank = web_app.run_pipeline_instrumented(img_blank)
print("\n--- TEST 2: Blank / Noisy Image ---")
print("status                   :", out_blank.get("status"))
print("route                    :", out_blank.get("route"))
print("destination              :", out_blank.get("destination"))
print("stages.ocr.engine        :", out_blank["stages"]["ocr"]["engine"])
print("stages.ocr.confidence    :", out_blank["stages"]["ocr"]["confidence"])
print("confidence_is_estimated :", out_blank["stages"]["ocr"]["confidence_is_estimated"])
print("spoken_phrase            :", out_blank.get("spoken_phrase"))

# Also test on test_images/images.jpg if available
import os
if os.path.exists("test_images/images.jpg"):
    img_real = cv2.imread("test_images/images.jpg")
    out_real = web_app.run_pipeline_instrumented(img_real)
    print("\n--- TEST 3: Real Image (test_images/images.jpg) ---")
    print("status                   :", out_real.get("status"))
    print("route                    :", out_real.get("route"))
    print("destination              :", out_real.get("destination"))
    print("stages.ocr.engine        :", out_real["stages"]["ocr"]["engine"])
    print("stages.ocr.confidence    :", out_real["stages"]["ocr"]["confidence"])
    print("confidence_is_estimated :", out_real["stages"]["ocr"]["confidence_is_estimated"])
    print("spoken_phrase            :", out_real.get("spoken_phrase"))
