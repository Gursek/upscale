"""Push calibrated Raspberry Pi readings to the hosted Upscale backend.

This bridge does not read GPIO or calibrate the HX711. It polls the existing,
working Pi-side HTTP service and transfers stable readings to Upscale.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import time

import requests


def required_environment():
    missing = [
        name
        for name in ("UPSCALE_SCALE_INGEST_URL", "SCALE_INGEST_API_KEY")
        if not os.getenv(name)
    ]
    if not os.getenv("SCALE_USER_ID") and not os.getenv("SCALE_USER_EMAIL"):
        missing.append("SCALE_USER_ID or SCALE_USER_EMAIL")
    if missing:
        raise ValueError(f"Missing required environment: {', '.join(missing)}")


def build_payload(reading, *, user_id=None, user_email=None, device_id="raspberry-pi"):
    payload = {
        "weight_kg": reading["weight_kg"],
        "stable": reading.get("stable", True),
        "captured_at": reading.get("captured_at")
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "device_id": device_id,
    }
    if user_id is not None:
        payload["user_id"] = int(user_id)
    elif user_email:
        payload["user_email"] = user_email
    else:
        raise ValueError("SCALE_USER_ID or SCALE_USER_EMAIL is required")
    return payload


def transfer_once(session=requests):
    required_environment()
    local_url = os.getenv("PI_SCALE_READ_URL", "http://127.0.0.1:5001/read")
    backend_url = os.environ["UPSCALE_SCALE_INGEST_URL"]
    api_key = os.environ["SCALE_INGEST_API_KEY"]
    timeout = float(os.getenv("SCALE_TRANSFER_TIMEOUT_SECONDS", "3"))

    local_response = session.get(local_url, timeout=timeout)
    local_response.raise_for_status()
    reading = local_response.json()
    if "weight_kg" not in reading:
        raise ValueError("Pi scale service response is missing weight_kg")
    if reading.get("stable") is False:
        return {"transferred": False, "reason": "unstable"}

    payload = build_payload(
        reading,
        user_id=os.getenv("SCALE_USER_ID"),
        user_email=os.getenv("SCALE_USER_EMAIL"),
        device_id=os.getenv("SCALE_DEVICE_ID", "raspberry-pi"),
    )
    result = session.post(
        backend_url,
        json=payload,
        headers={"X-Scale-Key": api_key},
        timeout=timeout,
    )
    result.raise_for_status()
    return {
        "transferred": True,
        "weight_kg": payload["weight_kg"],
        "device_id": payload["device_id"],
        "response": result.json(),
    }


def run_forever():
    interval = max(0.2, float(os.getenv("SCALE_PUSH_INTERVAL_SECONDS", "1")))
    retry_interval = max(interval, float(os.getenv("SCALE_RETRY_INTERVAL_SECONDS", "3")))
    while True:
        try:
            result = transfer_once()
            time.sleep(interval if result["transferred"] else 0.2)
        except (requests.RequestException, ValueError, KeyError) as exc:
            print(f"Scale transfer failed: {exc}", flush=True)
            time.sleep(retry_interval)


def main():
    parser = argparse.ArgumentParser(
        description="Transfer calibrated Raspberry Pi scale readings to UpScale."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Transfer one reading, print the result, and exit.",
    )
    args = parser.parse_args()

    if args.once:
        try:
            print(json.dumps(transfer_once(), indent=2), flush=True)
        except (requests.RequestException, ValueError, KeyError) as exc:
            parser.exit(1, f"Scale transfer failed: {exc}\n")
        return

    run_forever()


if __name__ == "__main__":
    main()
