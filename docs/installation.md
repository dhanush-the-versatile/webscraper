# Installation Guide

## Prerequisites

| Path | Requirements |
|---|---|
| **Docker (recommended)** | Docker ≥ 24 with the compose plugin |
| **Manual** | Python 3.12+, Node.js 22+, PostgreSQL 16 with the `pgvector` extension, Redis 7 |

## Option A — Docker (one command)

```bash
git clone <repo-url> && cd webscraper
./scripts/start.sh
```

What it does: creates `.env` from `.env.example` if missing, builds the
backend/frontend images, starts `db` (pgvector), `redis`, `backend` (runs
Alembic migrations on boot), `worker`, `beat`, `frontend`, and `nginx`.

Open:

- App: **http://localhost:8080**
- OpenAPI docs: **http://localhost:8080/docs**

Useful commands:

```bash
make logs       # tail backend + worker
make stop       # stop the stack
make clean      # stop and delete volumes (destroys data)
PUBLIC_PORT=9000 ./scripts/start.sh   # serve on a different port
```

## Option B — Manual (hot reload)

```bash
# 1) Infra
docker compose up -d db redis      # or use your own Postgres16+pgvector / Redis

# 2) Backend
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL="postgresql+asyncpg://talent:talent@localhost:5432/talent"
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3) Worker (optional — searches fall back to inline execution without it)
celery -A app.tasks.celery_app worker -Q search,maintenance --loglevel INFO

# 4) Frontend
cd ../frontend
npm install
npm run dev                        # http://localhost:3000 (proxies API to :8000)
```

`make dev` automates steps 1–4.

## Configuration reference

All settings come from environment variables (see `.env.example` for the full
annotated list). The important groups:

### Required for production

| Variable | Notes |
|---|---|
| `SECRET_KEY` | JWT signing key — `openssl rand -hex 32` |
| `POSTGRES_*` / `DATABASE_URL` | Database connection |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed origins |

### AI (optional — heuristic fallback without them)

| Variable | Notes |
|---|---|
| `LLM_PROVIDER` | `auto` (default) \| `openai` \| `anthropic` \| `heuristic` |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Chat + embeddings (`text-embedding-3-small`) |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Default model `claude-opus-4-8` |

### Data collection (optional — flagged sample data without them)

| Variable | Notes |
|---|---|
| `SERPAPI_API_KEY` | Licensed Google results API (preferred) |
| `BING_SEARCH_API_KEY` | Bing Web Search API |
| `GITHUB_TOKEN` | Raises GitHub REST rate limits for enrichment |

### Scraper behaviour

| Variable | Default | Notes |
|---|---|---|
| `SCRAPER_USER_AGENT` | `TalentDiscoveryBot/1.0 (+https://example.com/bot)` | Identify yourself honestly |
| `SCRAPER_RESPECT_ROBOTS` | `true` | Keep `true` in production |
| `SCRAPER_MAX_CONCURRENCY` | `5` | Global parallel fetch limit |
| `SCRAPER_MIN_DELAY_SECONDS` | `1.0` | Per-host pacing |
| `SCRAPER_REQUEST_TIMEOUT` / `SCRAPER_MAX_RETRIES` | `20` / `3` | Resilience |
| `SCRAPER_HTTP_PROXY` | – | Optional forward proxy (no restriction bypass) |

### OAuth login (optional)

Set `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` and/or
`GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET` plus `OAUTH_REDIRECT_BASE`. The
frontend exchanges the provider's authorization code via `POST /api/v1/auth/oauth`.

## Verifying the installation

```bash
curl http://localhost:8080/api/v1/health   # {"status":"ok",...}
make test                                  # 56 backend + 7 frontend tests
```

Register a user in the UI, run the example search, and you should see ranked
candidate cards within a few seconds (sample mode) — the AI-understood chips
show how the requirement was parsed.
