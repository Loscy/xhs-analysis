# Backend

FastAPI service for XHS goods tag extraction.

## Tables

- `api_keys`: global `sk-xxx` keys, SHA-256 hash only, optional expiry.
- `android_devices`: remote Android devices and reverse SSH/ADB tunnel metadata.
- `tag_queries`: query history, extracted tags, raw UI items, errors and latency.

## Local run

Requires Python 3.9+ and MySQL.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Create the first admin key:

```bash
cd backend
source .venv/bin/activate
python -m scripts.create_admin_key admin 2026-12-31T23:59:59
```
