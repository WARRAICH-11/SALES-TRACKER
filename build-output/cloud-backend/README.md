# Sales Tracker Cloud Backend (FastAPI)

Secure sync service for offline clients. Provides JWT auth, AES-256-GCM encrypted sync, conflict resolution, and admin analytics.

## Features
- JWT-based agent authentication
- Encrypted sync payloads (AES-256-GCM)
- Conflict resolution by `updated_at` (timestamp-based merge)
- Bulk upload of offline transactions
- Download latest product/customer data
- Admin dashboard (Plotly charts)
- SQLite by default; compatible with LiteFS for replication

## Stack
- FastAPI, Uvicorn
- SQLAlchemy + SQLite (or LiteFS in production)
- PyJWT, cryptography (AES-GCM)
- Plotly + Jinja2 for admin pages

## Setup
1. Create venv and install deps:
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate  # Windows
   pip install -r requirements.txt
   ```
2. Environment variables (create `.env` in `cloud-backend/`):
   ```env
   SECRET_KEY=change-this-super-secret
   SYNC_AES_KEY_BASE64=base64-32-bytes-key
   ADMIN_USER=admin
   ADMIN_PASS=admin123
   ```
   - Generate a 32-byte key: `python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"`
3. Run server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Endpoints
- POST `/auth/login` → JWT
- POST `/sync/upload` (JWT, AES-GCM payload) → upsert, conflict resolution, id mapping
- GET `/sync/download?since=ISO_DATE` (JWT) → products/customers changes since timestamp
- GET `/analytics/overview` (JWT, admin)
- GET `/analytics/top-products?start&end` (JWT, admin)
- GET `/admin` (browser) → dashboard

## LiteFS
SQLite works out-of-the-box. To run on Fly.io with LiteFS, mount the DB path and run this FastAPI service normally.

## Testing
- Run `python -m app.scripts.simulate_sync` to push 1,000 transactions and measure throughput. 