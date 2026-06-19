# Raspberry Pi Scale Connection

## Architecture

The Raspberry Pi reads and calibrates the HX711 locally. It then makes an
outbound HTTPS request to the hosted UpScale backend:

```text
Load cell -> HX711 -> Raspberry Pi reader -> local /read endpoint
          -> scale_push_bridge.py -> Render API -> Supabase PostgreSQL
          -> authenticated POS "Read Scale" button
```

The browser never connects directly to GPIO or to a private Raspberry Pi IP.

## 1. Calibrate the HX711

Use stable averaged raw readings, not a single sample:

1. Remove all weight and collect 20 to 50 raw samples.
2. Average them to get `tare_raw`.
3. Place a verified calibration mass, ideally 1 kg to 5 kg.
4. Collect and average another 20 to 50 samples to get `loaded_raw`.
5. Calculate the factor:

```bash
python backend/scripts/hx711_calibration.py \
  --tare-raw 1000 \
  --loaded-raw 51000 \
  --known-kg 5
```

Apply the result in the working Pi reader:

```text
weight_kg = (raw_reading - tare_offset) / counts_per_kg
```

A `tatobari_reference_unit_counts_per_gram` value is also printed. Use that
value for `HX711_REFERENCE_UNIT`, because `hx711v0_5_1.py` reports weight in
grams through `rawBytesToWeight()`.

A negative factor is valid when the load-cell wiring produces decreasing raw
counts as weight increases. Confirm calibration using at least two other known
weights before connecting the POS.

## 2. Install the tatobari Reader Adapter

Clone the upstream library on the Pi:

```bash
sudo git clone https://github.com/tatobari/hx711py.git /opt/hx711py
```

The adapter uses the repository's recommended `hx711v0_5_1.py` API and leaves
the upstream files unchanged. Copy
`deploy/raspberry-pi/hx711-service.env.example` to:

```text
/etc/upscale/hx711-service.env
```

Set the GPIO pins and the reference unit:

```env
HX711PY_PATH=/opt/hx711py
HX711_DOUT_PIN=5
HX711_PD_SCK_PIN=6
HX711_REFERENCE_UNIT=<tatobari_reference_unit_counts_per_gram>
```

Start it manually for the first test:

```bash
python backend/scripts/tatobari_hx711_service.py
```

The scale must be empty when the service starts because the adapter calls
`autosetOffset()` to tare it.

## 3. Verify the Local Reading

The adapter provides:

```http
GET http://127.0.0.1:5001/read
```

Example response:

```json
{
  "weight_kg": 1.275,
  "stable": true,
  "captured_at": "2026-06-19T08:30:00Z"
}
```

Requirements:

- `weight_kg` is the calibrated net weight in kilograms.
- `stable` is false while the reading is still moving.
- `captured_at` is UTC ISO-8601. The bridge supplies the current UTC time when
  this field is omitted.
- Do not send negative weights. Tare small zero drift locally.

Verify locally:

```bash
curl http://127.0.0.1:5001/read
```

Wait until `"stable": true`. The default stability rule requires at least six
samples within a 0.010 kg range. Adjust
`HX711_STABILITY_TOLERANCE_KG` only after testing the physical platform.

## 4. Configure Render

Generate a device secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set these Render environment variables:

```env
SCALE_INGEST_API_KEY=<generated-secret>
SCALE_INGEST_USER_ID=<UpScale owner user ID>
SCALE_DEVICE_ID=pi-vda-01
SCALE_MAX_AGE_SECONDS=10
SCALE_MAX_INGEST_AGE_SECONDS=60
SCALE_MAX_WEIGHT_KG=300
```

Deploy the migration that creates `scale_readings`. Render runs
`flask --app app:create_app db upgrade` during startup.

## 5. Configure the Raspberry Pi Bridge

Copy `deploy/raspberry-pi/scale-bridge.env.example` to:

```text
/etc/upscale/scale-bridge.env
```

Set:

```env
PI_SCALE_READ_URL=http://127.0.0.1:5001/read
UPSCALE_SCALE_INGEST_URL=https://your-render-api.example.com/api/scale/readings
SCALE_INGEST_API_KEY=<same-secret-as-render>
SCALE_USER_ID=<same-owner-user-id>
SCALE_DEVICE_ID=pi-vda-01
```

Install Python requirements in the Pi environment. The bridge only requires
`requests`.

## 6. Run a One-Shot Test

From the repository on the Pi:

```bash
python backend/scripts/scale_push_bridge.py --once
```

A successful response includes:

```json
{
  "transferred": true,
  "weight_kg": 1.275,
  "device_id": "pi-vda-01"
}
```

Then sign in to UpScale, select a per-kilogram product, and press **Read Scale**.
The displayed value should match the Pi reading within 0.001 kg.

## 7. Run Continuously

Review the paths and Linux user in both service files, then install them:

```bash
sudo mkdir -p /etc/upscale
sudo cp deploy/raspberry-pi/hx711-service.env.example /etc/upscale/hx711-service.env
sudo cp deploy/raspberry-pi/scale-bridge.env.example /etc/upscale/scale-bridge.env
sudo cp deploy/raspberry-pi/upscale-hx711.service /etc/systemd/system/
sudo cp deploy/raspberry-pi/upscale-scale-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now upscale-hx711
sudo systemctl enable --now upscale-scale-bridge
sudo systemctl status upscale-hx711
sudo systemctl status upscale-scale-bridge
```

View transfer logs:

```bash
journalctl -u upscale-scale-bridge -f
```

The upstream repository warns that Linux GPIO scheduling can occasionally
produce random HX711 values. The adapter's median and stability window reduce
that risk, but a load-cell system intended for commercial weighing still needs
physical repeatability testing and any applicable legal-metrology evaluation.

## Acceptance Check

Before using it for live sales:

- Empty platform reads `0.000 kg` after tare.
- Three known weights are within the required legal/mechanical tolerance.
- Unstable readings are not transferred.
- Disconnecting the Pi causes the POS to report a stale reading after 10 seconds.
- A different device ID or device secret is rejected.
- The final weight is still checked against available product stock by the POS
  and again by the invoice backend.
