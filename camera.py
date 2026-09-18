"""
camera.py
=========
Fast frame capture for the bus-route identifier.

Design note vs. the original brief: rather than writing a JPEG to
/dev/shm and reading it back, this module hands preprocessing a raw
numpy array straight out of Picamera2's `capture_array()`. That skips
JPEG encode/decode entirely, which on a Pi Zero 2 W is worth roughly
80-150ms — a meaningful chunk of a 1.5s budget. A `/dev/shm` debug dump
is still provided (`dump_last_frame_to_shm`) for when you want to eyeball
what the camera actually saw.

The camera is opened ONCE at process start (see main.py) and kept warm;
re-initializing Picamera2 per button press costs 300ms+ and would blow
the budget on its own.
"""
import time
import logging

import numpy as np

import config

logger = logging.getLogger("bus_route.camera")

try:
    from picamera2 import Picamera2
except ImportError:  # allows the module to be imported on a dev machine for testing
    Picamera2 = None


class CameraController:
    """Wraps a single warm Picamera2 instance for repeated fast captures."""

    def __init__(self, resolution=None, camera_format=None):
        self.resolution = resolution or config.CAMERA_RESOLUTION
        self.camera_format = camera_format or config.CAMERA_FORMAT
        self._picam2 = None
        self._last_frame = None

    def start(self):
        """Initialize and warm up the camera. Call once at boot."""
        if Picamera2 is None:
            raise RuntimeError(
                "picamera2 is not importable — are you running this on the Pi "
                "with libcamera installed, inside the system Python (not a "
                "venv without --system-site-packages)?"
            )
        self._picam2 = Picamera2()
        cfg = self._picam2.create_still_configuration(
            main={"size": self.resolution, "format": self.camera_format},
            buffer_count=2,  # double-buffer so capture doesn't stall on encode
        )
        self._picam2.configure(cfg)
        self._picam2.start()
        # Let AE/AWB settle once at boot so the FIRST real capture after a
        # button press isn't spent waiting on exposure convergence.
        time.sleep(0.6)
        logger.info("Camera warmed up at %sx%s", *self.resolution)

    def stop(self):
        if self._picam2 is not None:
            self._picam2.stop()
            self._picam2.close()

    def capture(self) -> np.ndarray:
        """
        Capture a single frame as an in-memory numpy array (H, W, 3).
        This is the hot-path call triggered by the button press.
        """
        if self._picam2 is None:
            raise RuntimeError("CameraController.start() was not called")
        t0 = time.monotonic()
        frame = self._picam2.capture_array("main")
        elapsed = time.monotonic() - t0
        logger.debug("Frame captured in %.3fs", elapsed)
        if elapsed > config.BUDGET_CAPTURE:
            logger.warning(
                "Capture took %.3fs, over the %.3fs budget", elapsed, config.BUDGET_CAPTURE
            )
        self._last_frame = frame
        return self._maybe_crop_roi(frame)

    def _maybe_crop_roi(self, frame: np.ndarray) -> np.ndarray:
        if not config.CAMERA_ROI:
            return frame
        h, w = frame.shape[:2]
        fx, fy, fw, fh = config.CAMERA_ROI
        x, y = int(fx * w), int(fy * h)
        cw, ch = int(fw * w), int(fh * h)
        return frame[y:y + ch, x:x + cw]

    def dump_last_frame_to_shm(self):
        """Debug helper: write the last captured frame to /dev/shm as JPEG."""
        if self._last_frame is None:
            logger.warning("No frame captured yet, nothing to dump")
            return
        import cv2  # local import: only needed for this debug path
        cv2.imwrite(str(config.SHM_FRAME_PATH), self._last_frame)
        logger.info("Dumped debug frame to %s", config.SHM_FRAME_PATH)


class MockCamera(CameraController):
    """Drop-in stand-in for CameraController when developing off-Pi.

    Loads a static test image instead of talking to real camera hardware,
    so you can iterate on preprocessing.py / ocr_engine.py on a laptop.
    """

    def __init__(self, test_image_path: str):
        super().__init__()
        self.test_image_path = test_image_path

    def start(self):
        logger.info("MockCamera active — using %s for every capture", self.test_image_path)

    def stop(self):
        pass

    def capture(self) -> np.ndarray:
        import cv2
        frame = cv2.imread(self.test_image_path)
        if frame is None:
            raise FileNotFoundError(self.test_image_path)
        return self._maybe_crop_roi(frame)
