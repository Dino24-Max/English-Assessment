# Setup Runbook

Quick setup guide for the Cruise Employee English Assessment Platform.

## Local Development (5–10 minutes)

### 1. Prerequisites

- Python 3.10+
- (Optional) PostgreSQL 15+ for production; SQLite used by default in development

### 2. Clone and Install

```bash
git clone <repository-url>
cd "Claude Demo"
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Variables

Create `.env` in project root (minimal for local dev):

```env
# Required in production; optional in dev (auto-generated if DEBUG=true)
DEBUG=true
SECRET_KEY=dev-only-change-in-production
ADMIN_API_KEY=your_admin_key

# Database (default: SQLite for dev)
DATABASE_URL=sqlite+aiosqlite:///./data/assessment.db

# Optional: PostgreSQL
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/assessment_db
```

#### Environment Variables: Dev vs Prod

| Variable | Development | Production |
|----------|-------------|------------|
| `DEBUG` | `true` – enables debug mode, auto-generates `SECRET_KEY` if missing | `false` – must be set explicitly |
| `SECRET_KEY` | Optional when `DEBUG=true`; can use `dev-only-change-in-production` | Required; use a long random string (e.g. `openssl rand -hex 32`) |
| `ADMIN_API_KEY` | Any value for local access; store securely | Strong random value; never commit to version control |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/assessment.db` (default) | `postgresql+asyncpg://user:pass@host:5432/dbname` recommended |
| `REDIS_URL` | Optional; not required for dev | Optional; use for sessions/rate limiting in production |
| `CSRF_SAME_SITE` | `lax` or `none` (if testing cross-origin) | `strict` or `lax` for security |

### 4. Run Server

```bash
python run_server.py
```

- App: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

### 5. Load Question Bank

```bash
python scripts/load_question_bank.py
```

Or via API (with admin key):

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/admin/load-full-question-bank" \
  -H "Content-Type: application/json" \
  -d '{"admin_key": "your_admin_key"}'
```

### 6. Run Tests

```bash
python -m pytest src/test/ -v
```

## Common Tasks

| Task | Command |
|------|---------|
| Start dev server | `python run_server.py` |
| Run tests | `python -m pytest src/test/ -v` |
| Load questions | `python scripts/load_question_bank.py` |
| Generate question bank | `python src/main/python/data/generate_question_bank.py` |
| Validate department flow | `python scripts/validate_department_flow.py` |
| Check admin | `python scripts/check_admin.py` |

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `SECRET_KEY required` | Set `DEBUG=true` or add `SECRET_KEY=...` to `.env` |
| `ADMIN_API_KEY required` | Add `ADMIN_API_KEY=...` to `.env` |
| DB connection error | Check `DATABASE_URL`; ensure PostgreSQL is running if used |
| No questions | Run `python scripts/load_question_bank.py` |
| CSRF errors in tests | Ensure tests send `X-CSRF-Token` header with valid token |

## References

- [API Documentation](../API_DOCUMENTATION.md)
- [Deployment Guide](../DEPLOYMENT.md)
- [Implementation Summary](../IMPLEMENTATION_SUMMARY.md)
- [CLAUDE.md](../CLAUDE.md) – development rules
