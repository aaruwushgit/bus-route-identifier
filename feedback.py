"""
feedback.py
===========
Audio (espeak-ng / Piper) and haptic (vibration motor) output.

Latency strategy, cheapest to most expensive:
  1. Pre-rendered cache hit (sounds/cache/<route>.wav)   -> ~10-20ms
  2. espeak-ng live synthesis (default TTS_ENGINE)        -> ~30-100ms
  3. Piper live synthesis (only if TTS_ENGINE="piper")    -> ~150ms-1s+
                                                              on a Zero 2 W

The cache is checked first regardless of engine, since even espeak-ng's
synthesis cost is worth skipping for routes you announce dozens of
times a day. See tools/pregenerate_cache.py to build it offline.

GPIO haptic driving uses gpiozero, which is the Raspberry Pi
Foundation's maintained recommendation for new projects (RPi.GPIO is
increasingly unsupported on current Raspberry Pi OS kernels; gpiozero
picks the right backend automatically). Motor pulsing runs in a
background thread so it never blocks the audio path or the main loop.
"""
import subprocess
import threading
import time
import logging
from pathlib import Path

import config

logger = logging.getLogger("bus_route.feedback")

try:
    from gpiozero import OutputDevice
except ImportError:  # allows import on a dev machine without GPIO hardware
    OutputDevice = None


# --------------------------------------------------------------------------
# Haptic
# --------------------------------------------------------------------------
class HapticMotor:
    def __init__(self, pin=None):
        pin = pin or config.VIBRATION_MOTOR_PIN
        try:
            self._device = OutputDevice(pin) if OutputDevice else None
        except Exception:
            logger.warning("Could not initialize haptic motor OutputDevice (no pin factory) — skipping haptics (dev mode).")
            self._device = None



    def _play_pattern(self, pattern):
        if self._device is None:
            logger.debug("HapticMotor: no GPIO backend, skipping (dev mode)")
            return
        for on_time, off_time in pattern:
            self._device.on()
            time.sleep(on_time)
            self._device.off()
            if off_time:
                time.sleep(off_time)

    def buzz_async(self, pattern):
        """Fire-and-forget so the caller (main loop) isn't blocked."""
        threading.Thread(target=self._play_pattern, args=(pattern,), daemon=True).start()

    def success(self):
        self.buzz_async(config.HAPTIC_SUCCESS_PATTERN)

    def low_confidence(self):
        self.buzz_async(config.HAPTIC_LOW_CONFIDENCE_PATTERN)

    def error(self):
        self.buzz_async(config.HAPTIC_ERROR_PATTERN)


# --------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------
def _cache_path_for(route: str) -> Path:
    safe_name = route.replace("/", "-")
    return config.AUDIO_CACHE_DIR / f"{safe_name}.wav"


def _play_wav(path: Path):
    try:
        subprocess.run(
            ["aplay", "-D", config.I2S_ALSA_DEVICE, str(path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        logger.warning("aplay not found — skipping playing %s (dev mode)", path)


def _synthesize_espeak(text: str, out_path: Path):
    try:
        subprocess.run(
            [
                "espeak-ng",
                "-v", config.ESPEAK_VOICE,
                "-s", str(config.ESPEAK_SPEED_WPM),
                "-w", str(out_path),
                text,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        logger.warning("espeak-ng not found — skipping synthesis of '%s' (dev mode)", text)


def _synthesize_piper(text: str, out_path: Path):
    try:
        proc = subprocess.run(
            [config.PIPER_BINARY, "--model", str(config.PIPER_MODEL_PATH), "--output_file", str(out_path)],
            input=text.encode("utf-8"),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc
    except FileNotFoundError:
        logger.warning("piper binary not found — skipping synthesis of '%s' (dev mode)", text)
        return None



def speak(text: str, cache_key: str = None):
    """
    Speak `text` immediately. If `cache_key` matches a pre-rendered clip
    (e.g. a route number), play that instead of synthesizing live.
    """
    t0 = time.monotonic()

    if cache_key:
        cached = _cache_path_for(cache_key)
        if cached.exists():
            _play_wav(cached)
            logger.debug("Played cached clip for '%s' in %.3fs", cache_key, time.monotonic() - t0)
            return

    tmp_path = Path("/dev/shm/tts_tmp.wav")
    if config.TTS_ENGINE == "piper":
        _synthesize_piper(text, tmp_path)
    else:
        _synthesize_espeak(text, tmp_path)
    _play_wav(tmp_path)

    elapsed = time.monotonic() - t0
    logger.debug("Synthesized+played '%s' in %.3fs", text, elapsed)
    if elapsed > config.BUDGET_FEEDBACK:
        logger.warning("Feedback took %.3fs, over the %.3fs budget", elapsed, config.BUDGET_FEEDBACK)


def announce_route(route: str, haptic: HapticMotor, destination: str = None):
    haptic.success()
    if destination:
        phrase = config.PHRASE_ROUTE_WITH_DESTINATION_TEMPLATE.format(route=route, destination=destination)
    else:
        phrase = config.PHRASE_ROUTE_TEMPLATE.format(route=route)
    speak(phrase, cache_key=route)



def announce_low_confidence(haptic: HapticMotor):
    haptic.low_confidence()
    speak(config.PHRASE_LOW_CONFIDENCE)


def announce_no_text(haptic: HapticMotor):
    haptic.error()
    speak(config.PHRASE_NO_TEXT)


def announce_low_battery(haptic: HapticMotor):
    haptic.buzz_async(config.HAPTIC_LOW_BATTERY_PATTERN)
    speak(config.PHRASE_LOW_BATTERY)


def announce_critical_battery(haptic: HapticMotor):
    haptic.buzz_async(config.HAPTIC_LOW_BATTERY_PATTERN)
    speak(config.PHRASE_CRITICAL_BATTERY)
