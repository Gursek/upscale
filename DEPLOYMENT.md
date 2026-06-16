# UpScale Deployment

## Target Setup

- Frontend: Vercel static site from `frontend/build`
- Backend API: Render web service from `backend`
- Database: Supabase PostgreSQL through `DATABASE_URL`
- Product images: Supabase Storage bucket named `product-images`

The hosted app is online-only. SQLite remains for local development and can
become an offline fallback later, but there is no SQLite to Supabase sync yet.

## Supabase

1. Create a Supabase project.
2. Copy the PostgreSQL connection string. Prefer the connection pooler string
   for hosted services.
3. Create a public Storage bucket named `product-images`.
4. Copy the project URL and service role key for the backend only.
5. Set backend environment variables:

```env
DATABASE_URL=postgresql://...
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=product-images
```

Do not put the service role key in Vercel or frontend code.

## Backend

Render uses `render.yaml`.

Set these env vars in Render:

```env
FLASK_ENV=production
AUTO_CREATE_DB=false
DATABASE_URL=postgresql://...
SECRET_KEY=...
JWT_SECRET_KEY=...
CORS_ORIGINS=https://your-vercel-domain.vercel.app
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=product-images
```

Start command:

```bash
flask --app app:create_app db upgrade && gunicorn --workers 2 --threads 4 --timeout 120 "app:create_app()"
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

## First Production Smoke Test

1. Open `/api/health` on the backend. It should return `{"status":"ok"}`.
2. Register/login through the Vercel frontend.
3. Add a product with an image.
4. Create a cash invoice.
5. Print/reprint the invoice.
6. Generate X-Reading and Z-Reading.
7. Export E-Journal and Activity Log.
