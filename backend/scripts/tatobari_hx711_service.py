"""Local HTTP adapter for tatobari/hx711py on a Raspberry Pi.

The service binds to loopback by default and exposes the calibrated, filtered
reading expected by scale_push_bridge.py:

    GET /read -> {"weight_kg": 1.275, "stable": true, "captured_at": "...Z"}

Keep tatobari/hx711py as a separate checkout and point HX711PY_PATH at it.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
import os
from pathlib import Path
import signal
import statistics
import sys
import threading
import time


def utc_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def reading_summary(samples, *, tolerance_kg, minimum_samples):
    values = [float(value) for value in samples]
    if not values:
        return {"weight_kg": 0.0, "stable": False, "spread_kg": None}

    median = statistics.median(values)
    spread = max(values) - min(values)
    stable = len(values) >= minimum_samples and spread <= tolerance_kg
    return {
        "weight_kg": round(max(0.0, median), 3),
        "stable": stable,
        "spread_kg": round(spread, 4),
    }


class ScaleState:
    def __init__(self, window_size, tolerance_kg, minimum_samples):
        self.samples = deque(maxlen=window_size)
        self.tolerance_kg = tolerance_kg
        self.minimum_samples = minimum_samples
        self.captured_at = None
        self.error = None
        self.lock = threading.Lock()

    def record(self, weight_kg):
        with self.lock:
            self.samples.append(weight_kg)
            self.captured_at = utc_iso()
            self.error = None

    def record_error(self, error):
        with self.lock:
            self.error = str(error)

    def snapshot(self):
        with self.lock:
            summary = reading_summary(
                self.samples,
                tolerance_kg=self.tolerance_kg,
                minimum_samples=self.minimum_samples,
            )
            return {
                **summary,
                "captured_at": self.captured_at,
                "sample_count": len(self.samples),
                "error": self.error,
            }


def load_hx711_class():
    library_path = Path(
        os.getenv("HX711PY_PATH", "/opt/hx711py")
    ).expanduser().resolve()
    if not library_path.exists():
        raise RuntimeError(f"HX711PY_PATH does not exist: {library_path}")
    sys.path.insert(0, str(library_path))
    return importlib.import_module("hx711v0_5_1").HX711


def create_hx711():
    hx711_class = load_hx711_class()
    dout_pin = int(os.getenv("HX711_DOUT_PIN", "5"))
    pd_sck_pin = int(os.getenv("HX711_PD_SCK_PIN", "6"))
    reference_unit = float(os.environ["HX711_REFERENCE_UNIT"])
    byte_order = os.getenv("HX711_BYTE_ORDER", "MSB")
    bit_order = os.getenv("HX711_BIT_ORDER", "MSB")

    hx = hx711_class(dout_pin, pd_sck_pin)
    hx.setReadingFormat(byte_order, bit_order)
    hx.autosetOffset()
    hx.setReferenceUnit(reference_unit)
    return hx


def sample_loop(hx, state, stop_event):
    sample_interval = max(0.02, float(os.getenv("HX711_SAMPLE_INTERVAL_SECONDS", "0.1")))
    zero_deadband = max(0.0, float(os.getenv("HX711_ZERO_DEADBAND_KG", "0.005")))
    while not stop_event.is_set():
        try:
            raw_bytes = hx.getRawBytes()
            weight_grams = float(hx.rawBytesToWeight(raw_bytes))
            weight_kg = weight_grams / 1000.0
            if abs(weight_kg) <= zero_deadband:
                weight_kg = 0.0
            state.record(weight_kg)
        except Exception as exc:
            state.record_error(exc)
        stop_event.wait(sample_interval)


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/read":
                self.send_error(404)
                return

            payload = state.snapshot()
            status = 200 if payload["captured_at"] else 503
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format_string, *args):
            if os.getenv("HX711_HTTP_LOG", "false").lower() == "true":
                super().log_message(format_string, *args)

    return Handler


def main():
    host = os.getenv("HX711_SERVICE_HOST", "127.0.0.1")
    port = int(os.getenv("HX711_SERVICE_PORT", "5001"))
    window_size = max(3, int(os.getenv("HX711_STABILITY_WINDOW", "8")))
    minimum_samples = max(3, int(os.getenv("HX711_MIN_STABLE_SAMPLES", "6")))
    tolerance_kg = max(0.001, float(os.getenv("HX711_STABILITY_TOLERANCE_KG", "0.010")))

    state = ScaleState(window_size, tolerance_kg, minimum_samples)
    stop_event = threading.Event()
    hx = create_hx711()
    sampling_thread = threading.Thread(
        target=sample_loop,
        args=(hx, state, stop_event),
        daemon=True,
    )
    sampling_thread.start()

    server = ThreadingHTTPServer((host, port), make_handler(state))

    def shutdown(_signum, _frame):
        stop_event.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    print(f"HX711 service listening on http://{host}:{port}/read", flush=True)
    try:
        server.serve_forever()
    finally:
        stop_event.set()
        sampling_thread.join(timeout=2)
        try:
            gpio = importlib.import_module("RPi.GPIO")
            gpio.cleanup()
        except Exception:
            pass
        server.server_close()


if __name__ == "__main__":
    main()
