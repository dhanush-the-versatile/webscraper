# Developer Guide

## Daily workflow

```bash
make dev    # Postgres+Redis in Docker; uvicorn --reload :8000; next dev :3000
make test   # backend pytest + frontend vitest
make lint   # ruff + tsc --noEmit
```

Backend hot-reloads via uvicorn; the frontend proxies `/api/backend/*` to
`localhost:8000` through the Next.js rewrite, so no CORS setup is needed.

## Project layout

```
backend/   FastAPI + SQLAlchemy + Celery + LangGraph pipeline (see docs/architecture.md)
frontend/  Next.js 15 App Router + Tailwind + TanStack Query + Zustand
docker/    nginx reverse-proxy config
scripts/   start.sh (prod), dev.sh, test.sh
docs/      this documentation set
```

## Testing

```bash
cd backend && pytest -q                    # 56 tests
pytest tests/test_api_search_flow.py -q    # one module
pytest -k "ranking" -q                     # by keyword

cd frontend && npx vitest run              # unit/component tests
npx vitest --watch
```

Conventions:

- Backend tests run on SQLite (aiosqlite) via the portable `Vector`/`JSONB`
  types; **migrations** are validated against real PostgreSQL+pgvector in CI.
- `tests/conftest.py` provides `db_session` (isolated in-memory DB),
  `app_client` (full app over a shared temp-file DB so background pipeline
  tasks see the same data), and `auth_headers`.
- The search-flow tests exercise the entire pipeline in sample mode — no
  network, no keys, deterministic results.

## Adding a public data source

Sources are pluggable — pick the right extension point in
`backend/app/scraping/sources/`:

### A) A new search provider (finds candidate URLs)

```python
# app/scraping/sources/my_search.py
from app.scraping.sources.base import SearchProvider
from app.scraping.models import SearchHit

class MySearchProvider(SearchProvider):
    name = "mysearch"

    def available(self) -> bool:
        return bool(settings.MYSEARCH_API_KEY)          # config-gated

    async def search(self, query, *, limit=10) -> list[SearchHit]:
        data = await http_client.get_json(...)           # official API please
        return [SearchHit(url=..., title=..., snippet=..., provider=self.name)]
```

Register it in `get_search_providers()` (`sources/search_engines.py`).

### B) A new profile enricher (turns a hit into a profile)

```python
# app/scraping/sources/dribbble.py
from app.scraping.sources.base import ProfileEnricher

class DribbbleEnricher(ProfileEnricher):
    name = "dribbble"

    def matches(self, hit) -> bool:
        return "dribbble.com/" in hit.url

    async def enrich(self, hit, requirement) -> CollectedProfile | None:
        ...  # fetch via official API or robots-gated page fetch
```

Register it in `build_default_registry()` (`scraping/pipeline.py`) **before**
`GenericWebEnricher` (first match wins). The generic enricher already handles
any robots-allowed public page, so a dedicated enricher is only needed when a
site has an official API or special parsing.

Compliance rules for any new source: prefer the official API; never fetch
auth-walled pages; respect robots.txt (`http_client.get` does this for you);
extract only what is publicly displayed.

### C) A new query template

Add one line to `_SITE_TEMPLATES` in `app/ai/query_generation.py` (plus an
optional relevance gate).

## Adding an LLM provider

Implement `LLMProvider` (`app/ai/provider.py`) with `acomplete_json()` and add
a branch in `get_llm_provider()`. Return `None` on any failure — callers
always fall back to heuristics.

## Database changes

```bash
cd backend
# edit app/models/*.py, then:
DATABASE_URL=postgresql+asyncpg://talent:talent@localhost:5432/talent \
  alembic revision --autogenerate -m "add my_table"
# review the generated file (custom Vector/JSONB types render correctly), then:
alembic upgrade head
```

## Frontend conventions

- Server state lives in TanStack Query hooks (`src/hooks/use-api.ts`) — add
  new endpoints there, typed against `src/types/api.ts` (keep it mirroring the
  backend schemas).
- Client state (auth tokens, UI prefs) lives in Zustand stores.
- UI primitives in `components/ui/*` follow the shadcn/cva pattern — extend
  variants rather than sprinkling ad-hoc classes.
- Forms: React Hook Form + Zod resolver (see login/register/search pages).
- Charts: keep to the dashboard conventions — one validated hue per mode,
  solid hairline grids, tooltips + table-view twins for ranked charts.

## Code quality bar

- Python: ruff (`E,F,I,B,UP,C4,SIM,ASYNC`), full type hints, async
  throughout; services own transactions; no ORM access from routers.
- TypeScript: `strict`, no `any` in app code; components must render without
  runtime warnings.
- Every module lands with tests; CI must be green (lint + migrations + both
  test suites + docker builds).
