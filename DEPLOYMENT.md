# UpScale Deployment

## Target Setup

- Frontend: Vercel static site from `frontend/build`
- Backend API: Render web service from `backend`
- Database: Supabase PostgreSQL through `DATABASE_URL`
- Product images: Supabase Storage bucket named `product-images`

The hosted app is online-only. SQLite remains for local development and can
become an offline fallback later, but there is no SQLite to Supabase sync yet.

## Supabase Sync

The `invoices.synced` column exists only as a reserved field for a future
Supabase sync worker. It is not active in the current hosted app, and the
dashboard intentionally shows cloud sync as "coming soon" instead of displaying
a misleading unsynced count.

To activate sync later, build a queue that marks locally created records as
unsynced, pushes them to Supabase when connectivity returns, verifies the remote
write, then marks the local record as synced. Add conflict handling, retry
backoff, and visible sync status before exposing any sync count to users.

## Raspberry Pi Scale Transfer

The working HX711/load-cell service remains on the Raspberry Pi. The transfer
bridge at `backend/scripts/scale_push_bridge.py` polls that existing local
service and sends stable readings to the hosted backend through an authenticated
outbound HTTPS request.

Set these backend variables on Render:

```env
SCALE_INGEST_API_KEY=<long-random-device-secret>
SCALE_INGEST_USER_ID=<owner-user-id>
SCALE_DEVICE_ID=pi-vda-01
SCALE_MAX_AGE_SECONDS=10
SCALE_MAX_INGEST_AGE_SECONDS=60
SCALE_MAX_WEIGHT_KG=300
```

Set these variables on the Raspberry Pi:

```env
PI_SCALE_READ_URL=http://127.0.0.1:5001/read
UPSCALE_SCALE_INGEST_URL=https://your-api-domain.onrender.com/api/scale/readings
SCALE_INGEST_API_KEY=<same-device-secret>
SCALE_USER_ID=<owner-user-id>
SCALE_DEVICE_ID=pi-vda-01
SCALE_PUSH_INTERVAL_SECONDS=1
SCALE_TRANSFER_TIMEOUT_SECONDS=3
```

Run the bridge under `systemd` or another process supervisor. The POS accepts
only the latest reading within `SCALE_MAX_AGE_SECONDS`; older readings return a
stale-reading error instead of being applied to a sale.

The complete calibration, one-shot transfer test, and `systemd` installation
steps are in `RASPBERRY_PI_SCALE.md`.

## Supabase

1. Create a Supabase project.
2. Copy the PostgreSQL connection string. Prefer the connection pooler string
   for hosted services and local setup if the direct database host does not
   resolve. The pooler is usually IPv4-friendly; the direct
   `db.<project-ref>.supabase.co` host may fail on networks without IPv6.
3. Create a public Storage bucket named `product-images`.
4. Copy the project URL and service role key for the backend only.
5. Set backend environment variables:

```env
DATABASE_URL=postgresql://...
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=product-images
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=notifications@example.com
SMTP_PASSWORD=...
SMTP_FROM=notifications@example.com
```

Do not put the service role key in Vercel or frontend code.

## Backend

Render can be created from `render.yaml` as a Blueprint. The current
configuration runs from the repo root:

```bash
pip install -r requirements.txt
cd backend && flask --app app:create_app db upgrade && gunicorn --workers 2 --threads 4 --timeout 120 wsgi:app
```

If you created the Render service manually, use the same root-relative
commands:

```bash
pip install -r requirements.txt
cd backend && flask --app app:create_app db upgrade && gunicorn --workers 2 --threads 4 --timeout 120 wsgi:app
```

The repo also has a root `requirements.txt` that forwards to
`backend/requirements.txt`. The start command must run inside `backend`, because
that is where `app.py` and the migration folder live.

Set these env vars in Render:

```env
FLASK_ENV=production
AUTO_CREATE_DB=false
DATABASE_URL=postgresql://...
SECRET_KEY=...
JWT_SECRET_KEY=...
CORS_ORIGINS=https://upscale-kappa.vercel.app
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=product-images
```

## Frontend

Deploy the `frontend` directory to Vercel.

Set this Vercel environment variable:

```env
VITE_API_BASE_URL=https://your-api-domain.onrender.com/api
```

Build settings:

- Install command: `npm ci`
- Build command: `npm run build`
- Output directory: `build`

If you leave the Vercel project root as the repository root instead, the root
`vercel.json` delegates to the frontend folder:

- Install command: `cd frontend && npm ci`
- Build command: `cd frontend && npm run build`
- Output directory: `frontend/build`

## First Production Smoke Test

1. Open `/api/health` on the backend. It should return `{"status":"ok"}`.
2. Register/login through the Vercel frontend.
3. Add a product with an image.
4. Create a cash invoice.
5. Print/reprint the invoice.
6. Generate X-Reading and Z-Reading.
7. Export E-Journal and Activity Log.
