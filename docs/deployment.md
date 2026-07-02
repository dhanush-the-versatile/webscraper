# Deployment Guide

## Reference topology (docker-compose)

`docker compose up -d --build` gives you the full production topology on one
host:

| Service | Image | Role |
|---|---|---|
| `nginx` | nginx:1.27-alpine | Public entrypoint (`:8080` by default), routes `/` → frontend, `/api/backend/*` + `/api/v1/*` + `/docs` → backend |
| `frontend` | built (Next standalone) | React app, non-root user |
| `backend` | built (gunicorn+uvicorn workers) | REST API; runs `alembic upgrade head` on boot |
| `worker` | same image | Celery queues `search`, `maintenance` |
| `beat` | same image | Periodic tasks (cache refresh, purge) |
| `db` | pgvector/pgvector:pg16 | PostgreSQL + vector extension, named volume |
| `redis` | redis:7-alpine | Cache + Celery broker/results |

## Production checklist

1. **Secrets** — set in `.env` (never commit):
   - `SECRET_KEY` = `openssl rand -hex 32`
   - strong `POSTGRES_PASSWORD`
   - `ENVIRONMENT=production`, `LOG_JSON=true`
2. **TLS** — terminate HTTPS in front of nginx (cloud LB, Caddy, certbot) or
   extend `docker/nginx/nginx.conf` with a 443 server block + certificates.
3. **CORS** — `BACKEND_CORS_ORIGINS=https://your-domain.example`.
4. **Scraper identity** — set `SCRAPER_USER_AGENT` to a real contact URL;
   keep `SCRAPER_RESPECT_ROBOTS=true`.
5. **API keys** — add LLM + search keys for live mode; `GITHUB_TOKEN` for
   comfortable GitHub API limits.
6. **OAuth** — register Google/GitHub apps, set client IDs/secrets and
   `OAUTH_REDIRECT_BASE=https://your-domain.example`.

## Scaling

| Pressure point | Lever |
|---|---|
| Search throughput | `docker compose up -d --scale worker=4`; raise `--concurrency` per worker |
| API throughput | Increase gunicorn `--workers` (CMD in `backend/Dockerfile`) or scale `backend` behind nginx `least_conn` |
| Collection politeness vs speed | `SCRAPER_MAX_CONCURRENCY`, `SCRAPER_MIN_DELAY_SECONDS` |
| DB | Managed PostgreSQL with pgvector (RDS/Aurora, Cloud SQL, Neon, Supabase all ship it); point `DATABASE_URL` at it and drop the `db` service |
| Cache/broker | Managed Redis; set `REDIS_HOST`/`CELERY_*` |

The backend is stateless (JWT, no sessions); exports stream in-response — no
shared volume needed. All services are horizontally scalable except `beat`
(run exactly one).

## Migrations

- Applied automatically by the backend container (`RUN_MIGRATIONS=true`).
- Manual control: `docker compose run --rm -e RUN_MIGRATIONS=false backend alembic upgrade head`
- Rollback one revision: `… alembic downgrade -1`

## Backups

```bash
# dump
docker compose exec db pg_dump -U talent talent | gzip > backup-$(date +%F).sql.gz
# restore
gunzip -c backup-2026-07-02.sql.gz | docker compose exec -T db psql -U talent talent
```

Schedule via cron; volumes `pgdata`/`redisdata` can also be snapshotted.

## Monitoring & logs

- All services log JSON to stdout (`LOG_JSON=true`) — ship with your
  collector of choice (Loki, CloudWatch, Datadog). Every API line carries a
  `request_id`; worker logs carry `search_id`.
- Health endpoints: `/api/v1/health` (liveness), `/api/v1/ready` (DB check) —
  wired into the backend container's `HEALTHCHECK`; compose gates startup on
  `db`/`redis` health.
- Audit trail: `audit_logs` table (registrations, logins, failures).

## CI/CD

`.github/workflows/ci.yml` runs on every push/PR:

1. **backend** — ruff lint; Alembic `upgrade → downgrade → upgrade` against a
   real pgvector Postgres service; pytest with coverage.
2. **frontend** — tsc typecheck, vitest, production `next build`.
3. **docker** — builds both images with GHA layer caching.

Extend with a push stage (GHCR/ECR) and a deploy job (SSH + `docker compose
pull && up -d`, or your platform's action) once you have a registry/host.

## Zero-key production note

Without search API keys the platform serves clearly-flagged sample profiles.
That is a **demo mode** — for real sourcing configure `SERPAPI_API_KEY` (or
`BING_SEARCH_API_KEY`) and at least one LLM key, and review the terms of every
data source you enable against your jurisdiction and use case.
