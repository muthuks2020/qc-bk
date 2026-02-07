# Appasamy QC Application — Backend API

REST API for the Appasamy Associates QC Application (B-SCAN ophthalmic product line).

**Stack:** Python 3.11+ · Flask · SQLAlchemy · Marshmallow · PostgreSQL  
**Deploy:** AWS EC2 · Nginx · Gunicorn  
**Integration:** Odoo ERP (XML-RPC)

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Git

### Setup

```bash
# 1. Clone and enter project
git clone <repo-url>
cd appasamy-qc-api

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create local database
createdb appasamy_qc            # or via pgAdmin / psql
# Then run the schema:
psql -d appasamy_qc -f db/qc_holistic_schema_v4.sql

# 5. Copy env and configure
cp .env.example .env
# Edit .env — all defaults work out of the box for local dev

# 6. Seed initial data
python seed.py

# 7. Run the dev server
flask --app wsgi:app run --debug --port 5000

# 8. Test it
curl http://localhost:5000/api/v1/health
```

### Testing API Endpoints

All requests require auth headers:

```bash
curl -H "Authorization: Bearer local-dev-token-2026" \
     -H "X-User-Id: 1" \
     -H "X-User-Name: Admin User" \
     -H "X-User-Role: admin" \
     -H "X-User-Email: admin@appasamy.com" \
     http://localhost:5000/api/v1/lookups/categories
```

Switch roles by changing `X-User-Role` to: `admin`, `maker`, `checker`, `approver`, `gate_entry`, `store_keeper`

---

## API Endpoints (Stage 1 — 82 endpoints)

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 1 | GET | `/api/v1/health` | Health check (no auth) |
| 2-4 | CRUD | `/api/v1/departments` | Department management |
| 5-8 | CRUD | `/api/v1/categories` | Product categories |
| 9-12 | CRUD | `/api/v1/categories/<id>/groups` | Product groups |
| 13-15 | CRUD | `/api/v1/units` | Units of measurement |
| 16-19 | CRUD | `/api/v1/instruments` | Measuring instruments |
| 20-23 | CRUD | `/api/v1/vendors` | Vendor/supplier master |
| 24-29 | CRUD+ | `/api/v1/sampling-plans` | Sampling plans + calculate |
| 30-34 | CRUD | `/api/v1/qc-plans` | QC plans with stages/params |
| 35-44 | CRUD+ | `/api/v1/components` | Component master (full CRUD, duplicate, export, upload) |
| 45-48 | CRUD | `/api/v1/defect-types` | Defect type master |
| 49-52 | CRUD | `/api/v1/rejection-reasons` | Rejection reasons |
| 53-56 | CRUD | `/api/v1/locations` | Warehouse locations |
| 57-58 | RU | `/api/v1/system-config` | System configuration |
| 59-71 | GET | `/api/v1/lookups/*` | Lightweight dropdown data |

---

## Project Structure

```
appasamy-qc-api/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Config classes
│   ├── extensions.py            # SQLAlchemy, Marshmallow, CORS, Limiter
│   ├── models/                  # SQLAlchemy models (mapped to existing tables)
│   ├── schemas/                 # Marshmallow validation schemas
│   ├── routes/                  # Blueprint route handlers
│   ├── services/                # Business logic services
│   ├── middleware/               # Auth, error handling
│   └── utils/                   # Pagination, responses, validators, audit
├── db/                          # Database schema SQL
├── seed.py                      # Seed data for dev
├── wsgi.py                      # Gunicorn entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## Production Deployment

```bash
# Install with Gunicorn
pip install -r requirements.txt

# Run with Gunicorn
gunicorn wsgi:app -w 4 -b 0.0.0.0:8000

# Nginx config
# See deployment docs for full nginx.conf with SSL
```

---

## Environment Variables

See `.env.example` for all available configuration. Key toggles:
- `ODOO_ENABLED=false` — Odoo integration off for local dev
- `UPLOAD_STORAGE=local` — Files saved to disk (not S3)
- `EMAIL_ENABLED=false` — No SMTP required locally
- `SCHEDULER_ENABLED=false` — No background jobs locally
