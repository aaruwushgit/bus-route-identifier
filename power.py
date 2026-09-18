"""
power.py
========
Battery-level monitoring — the one piece of "idle power management"
that actually belongs inside the Python process. Everything else
discussed as a power-saving feature (CPU governor, disabling HDMI/BT,
etc.) happens at the OS level before main.py starts — see
scripts/power_saving.sh and SOFTWARE_AND_HARDWARE_GUIDE.md section 4.

Honesty note: this does NOT put the Pi Zero 2 W to sleep. There is no
supported deep-sleep state on this board without extra PMIC hardware
(a PiSugar, a TPL5110 timer, or similar) that cuts and restores power
externally. What this module DOES do is warn the user before the
device dies mid-journey, which for an assistive device matters more
than shaving milliwatts — a bus route reader that silently dies is a
worse failure mode than one that's slightly less power-efficient.

Hardware assumed: a simple resistor voltage divider from the LiPo's
raw voltage into an ADS1115 (I2C ADC) channel. Any other ADC works the
same way — swap out `_read_raw_voltage`.
"""
import logging
import threading
import time

import config

logger = logging.getLogger("bus_route.power")

try:
    import board
    import busio
    from adafruit_ads1x15.ads1115 import ADS1115
    from adafruit_ads1x15.analog_in import AnalogIn
except ImportError:  # allows import on a dev machine without the ADC wired up
    board = busio = ADS1115 = AnalogIn = None


class BatteryMonitor:
    """
    Polls battery voltage on a background thread at a low frequency
    (config.BATTERY_CHECK_INTERVAL_S) and fires a callback when
    thresholds are crossed. Deliberately NOT on the button-press hot
    path — checking battery voltage has no business adding latency to
    a route lookup.
    """

    def __init__(self, on_low, on_critical):
        self._on_low = on_low
        self._on_critical = on_critical
        self._stop_event = threading.Event()
        self._thread = None
        self._last_state = "ok"  # "ok" -> "low" -> "critical", never goes back down
        self._ads = None

        if config.POWER_MONITORING_ENABLED and ADS1115 is not None:
            i2c = busio.I2C(board.SCL, board.SDA)
            self._ads = ADS1115(i2c)
        elif config.POWER_MONITORING_ENABLED:
            logger.warning(
                "POWER_MONITORING_ENABLED but adafruit-circuitpython-ads1x15 "
                "is not installed — battery monitoring will be a no-op. "
                "pip install adafruit-circuitpython-ads1x15"
            )

    def start(self):
        if not config.POWER_MONITORING_ENABLED:
            logger.info("Battery monitoring disabled (config.POWER_MONITORING_ENABLED=False)")
            return
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("Battery monitor started, polling every %ss", config.BATTERY_CHECK_INTERVAL_S)

    def stop(self):
        self._stop_event.set()

    def _poll_loop(self):
        while not self._stop_event.is_set():
            try:
                voltage = self._read_voltage()
                if voltage is not None:
                    self._evaluate(voltage)
            except Exception:
                logger.exception("Battery read failed — will retry next interval")
            self._stop_event.wait(config.BATTERY_CHECK_INTERVAL_S)

    def _read_voltage(self):
        if self._ads is None:
            return None
        channel = AnalogIn(self._ads, config.BATTERY_ADC_CHANNEL)
        return channel.voltage * config.BATTERY_VOLTAGE_DIVIDER_RATIO

    def _evaluate(self, voltage: float):
        logger.debug("Battery voltage: %.2fV", voltage)
        if voltage <= config.BATTERY_CRITICAL_VOLTAGE:
            if self._last_state != "critical":
                logger.warning("Battery CRITICAL: %.2fV", voltage)
                self._last_state = "critical"
                self._on_critical()
        elif voltage <= config.BATTERY_LOW_VOLTAGE:
            if self._last_state == "ok":
                logger.warning("Battery LOW: %.2fV", voltage)
                self._last_state = "low"
                self._on_low()
