# TeleBot V2 - Enterprise Workflow Extension

This V2 layer extends the existing project without removing old endpoints or UI.

## 1) What was added

- Premium dashboard UI: `static/v2/index.html`
- Light/Dark mode + responsive layout + chart widgets
- Access request workflow API with admin decisions
- Upload intelligence APIs with preview and header validation
- New data models:
  - `access_requests`
  - `upload_logs`
  - `admin_logs`
  - `excel_data`
- Telegram command extensions:
  - `/help`
  - `/request_access`
  - `/status`
  - `/upload`
  - `/search`
  - `/dashboard`
- Telegram inline admin actions:
  - Approve
  - Reject
  - Block

## 2) Why this architecture

- Non-breaking: Existing routes and frontend remain intact.
- Modular: New V2 routes are isolated under `/api/v2`.
- Observable: Upload and admin action logs are persisted.
- Safer ingestion: Header normalization and required-field validation before inserts.

## 3) New API endpoints

- `GET /api/v2/dashboard/stats`
- `GET /api/v2/access-requests`
- `PATCH /api/v2/access-requests/{id}?decision=approve|reject|block`
- `GET /api/v2/search`
- `POST /api/v2/uploads/preview?dataset=daywise|nwa`
- `POST /api/v2/uploads/import?dataset=daywise|nwa`
- `GET /api/v2/uploads/logs`
- `GET /api/v2/activity/logs`

## 4) Startup and usage

From the app root (the folder that contains `src/` and `static/`):

```powershell
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

Open V2 UI:

- `http://10.138.25.47:8001/dashboard`
- or `http://10.138.25.47:8001/dashboard-v2`

## 5) Environment recommendations

Add these in `.env`:

- `TELEGRAM_BOT_TOKEN=...`
- `TELEGRAM_MODE=polling`
- `SECRET_KEY=...`
- `ACCESS_TOKEN_EXPIRE_MINUTES=60`
- `API_BASE_URL=http://10.138.25.47:8001`
- `BACKEND_URL=http://10.138.25.47:8001`
- `FRONTEND_URL=http://10.138.25.47:8001`
- `WEBHOOK_URL=http://10.138.25.47:8001/webhook`
- `WS_URL=ws://10.138.25.47:8001/ws`
- `WEB_DASHBOARD_V1_URL=http://10.138.25.47:8001/dashboard`
- `WEB_DASHBOARD_V2_URL=http://10.138.25.47:8001/dashboard-v2`
- `CORS_ALLOW_ORIGINS=http://10.138.25.47:8001`
- `UVICORN_HOST=0.0.0.0`
- `UVICORN_PORT=8001`

## 6) Deployment guide

1. Use a process manager (`systemd`, `supervisor`, or container orchestration).
2. Reverse proxy with Nginx/Caddy/Apache.
3. Put TLS in front of FastAPI.
4. Store SQLite file on persistent volume.
5. Enable app log rotation.
6. Rotate Telegram bot token if exposed.
7. Change only the `.env` URL variables for future IP/domain moves.

## 7) Scale path

- Move SQLite to PostgreSQL.
- Add Redis for queue/background workers.
- Add Celery/RQ for heavy Excel processing.
- Add WebSocket notifications for live dashboard updates.
