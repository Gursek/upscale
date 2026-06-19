# Upscale Revision Changelog

## Codebase

- Added a persistent `scale_readings` table and migration for calibrated Raspberry Pi measurements.
- Added `POST /api/scale/readings`, an authenticated device endpoint for outbound Pi-to-backend transfers.
- Changed `GET /api/scale/read` to return the latest reading for the signed-in business and reject stale data.
- Added validation for device credentials, business-account binding, unstable readings, invalid weights, old timestamps, future timestamps, and configured maximum weight.
- Added `backend/scripts/scale_push_bridge.py`. It polls the authors' existing Pi-side reading service and transfers stable readings to the hosted backend without replacing the working HX711 or calibration code.
- Updated the POS scale action to display backend errors instead of silently accepting an invalid response.
- Added four hardware-independent transfer tests covering successful transfer, mocked Pi polling, invalid credentials, unstable readings, and stale-reading rejection.
- Documented Render and Raspberry Pi environment variables and deployment behavior in `DEPLOYMENT.md` and `.env.example`.
- Updated `BIR_COMPLIANCE.md` to describe the completed outbound transfer path.

## Research Paper

### Chapter I

- Re-centered the Background of the Study on manual weighing, calculator billing, handwritten records, and stock monitoring in meatshop operations.
- Added one concise survey paragraph based on the verified instrument and both identical result workbooks (`n = 20`).
- Reported the validated operator findings for billing errors, stock shortages, stock-counting time, checkout delay, perceived usefulness, willingness to adopt, overall concerns, and staff adaptability.
- Rewrote the weighing paragraph to describe the completed load-cell, HX711, Raspberry Pi, calibration, and authenticated transfer pipeline.
- Reworked the Statement of the Problem and Specific Objectives into five directly corresponding items.
- Added conceptual and operational definitions for Load Cell, HX711 Module, and Calibration and Tare.
- Simplified the Scale Transfer Service, API, and database definitions for non-technical readers.
- Updated Scope and Limitations so scale integration is a completed capability and remaining limitations appear once.

### Chapter II

- Added subsection **2.1.3 On Load-Cell and HX711 Weight Sensing**.
- Added and cited the AVIA Semiconductor HX711 data sheet.
- Updated the synthesis to treat digital weighing and transfer as completed.
- Simplified the description of the linked activity log.

### Chapter III

- Added the market survey to the APF Version Scope and requirements-gathering activity.
- Updated Cycle Plan, Cycle Build, Client Checkpoint, and Post-Version Review to describe the completed sensor and transfer work.
- Rewrote Technicality of the Project around the connected-store architecture and outbound Pi-to-cloud transfer.
- Replaced the former incomplete scale-service discussion with completed Load Cell, HX711, Raspberry Pi, and Scale Transfer Bridge descriptions.
- Rewrote How the Project Works to explain tare, calibration, stable reading capture, authenticated transfer, freshness checking, checkout, and stock deduction.

## Verification

- Both survey result workbooks have the same SHA-256 hash and identical values.
- Survey instrument wording, consent language, optional identifiers, and five-point scale were checked against `Upscale_Survey_Likert.docx`.
- Scale transfer tests: 4 passed.
- Frontend static diagnostics: 0 errors and 0 warnings.
- DOCX accessibility audit: 0 findings.
- The full backend suite reported 38 passes and 2 unrelated date-dependent failures in compliance tests that assume the current business date is June 17, 2026.
