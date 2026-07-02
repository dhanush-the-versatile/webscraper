# Talent Discovery Platform

AI-powered talent sourcing: a recruiter types a requirement in plain language —

> *“Find senior React developers with TypeScript and 5+ years in Berlin, Germany”*

— and the platform understands it with an LLM, generates optimized search queries, collects **publicly available** professional profiles from multiple sources in parallel, deduplicates them, ranks every candidate with a 0–100 score breakdown, and presents the results in a modern dashboard with AI-written summaries and explanations.

![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=nextdotjs)
![License](https://img.shields.io/badge/data-public_sources_only-16a34a)

---

## Feature highlights

| Area | What you get |
|---|---|
| **AI understanding** | LangGraph pipeline: NL requirement → structured spec (titles, skills, seniority, years, location, industry, …) with deterministic fallback when no LLM key is set |
| **Query generation** | Per-source optimized queries (`site:linkedin.com/in …`, `site:github.com …`, portfolio/team-page variants), source-aware (design roles → Behance/Dribbble, data roles → Kaggle) |
| **Public data collection** | Modular pipeline: search → collect URLs → fetch public pages → extract → clean → normalize → dedupe → store. Retry, timeout, parallel async execution, Redis caching, per-host pacing, robots.txt compliance, configurable UA, optional proxy |
| **Sources** | GitHub + Stack Overflow via **official APIs**, LinkedIn via **search-snippets only** (never fetched), portfolios / company team pages / Medium / Dev.to / Kaggle / Behance / Dribbble / research pages via robots-gated extraction, SerpAPI/Bing search APIs |
| **Ranking** | 0–100 breakdown: skill, experience, technology, location, portfolio, GitHub activity, semantic relevance (pgvector embeddings) + overall score, AI summary and ranking explanation per candidate |
| **Search** | Keyword, structured filters, semantic (pgvector cosine), hybrid |
| **Frontend** | Next.js 15 + React 19: dashboard, search with live pipeline progress, candidate cards & detail, saved list, notes, history, Recharts analytics, dark mode, responsive |
| **Platform** | JWT auth (+ Google/GitHub OAuth code exchange), RBAC, rate limiting, audit log, exports (CSV/XLSX/PDF/JSON), Celery workers + beat, structured logging |

### Honest offline mode

With **zero API keys** the platform still runs end-to-end: AI falls back to a curated-taxonomy parser and search falls back to a deterministic **sample-data provider whose profiles are clearly flagged as samples** in the UI and API. Add `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` and `SERPAPI_API_KEY`/`BING_SEARCH_API_KEY` to switch to live AI + live collection — no code changes.

---

## Quick start (one command)

```bash
git clone <repo-url> && cd webscraper
./scripts/start.sh          # or: make start
```

Then open **http://localhost:8080** (API docs at `/docs`). The script creates `.env` from `.env.example` on first run — set a real `SECRET_KEY` and any API keys you have.

### Local development (hot reload)

```bash
make dev        # Postgres+Redis in Docker; uvicorn --reload + next dev locally
make test       # backend pytest + frontend vitest
```

---

## Architecture at a glance

```
Browser ── Nginx ──┬── Next.js 15 (dashboard, search, analytics…)
                   └── FastAPI ──┬── PostgreSQL 16 + pgvector
                                 ├── Redis (cache + broker)
                                 └── Celery workers ── LangGraph pipeline
                                        understand → generate queries → collect → rank
                                              │             │              │
                                          LLM provider   search APIs   official APIs +
                                          (or heuristics) (or samples)  robots-gated fetch
```

- **Clean architecture**: models → repositories → services → API, DI via FastAPI dependencies.
- **Every AI capability degrades gracefully** — the pipeline never hard-depends on an external service.
- **Adding a source** = implement one `SearchProvider` or `ProfileEnricher` and register it ([guide](docs/development.md#adding-a-public-data-source)).

Full details: [docs/architecture.md](docs/architecture.md)

---

## Documentation

| Doc | Contents |
|---|---|
| [docs/installation.md](docs/installation.md) | Prerequisites, Docker & manual setup, configuration reference |
| [docs/architecture.md](docs/architecture.md) | System diagram, module map, data model, pipeline internals |
| [docs/api.md](docs/api.md) | REST endpoints, auth flow, request/response examples |
| [docs/deployment.md](docs/deployment.md) | Production checklist, scaling, TLS, backups, monitoring |
| [docs/development.md](docs/development.md) | Dev workflow, tests, adding sources/providers, conventions |

---

## Compliance & ethics (by design)

- Collects **only publicly available** professional information; provenance stored per candidate.
- **robots.txt honored** on every page fetch; per-host request pacing; identifiable user agent.
- **Official APIs preferred**: GitHub REST, StackExchange, licensed search APIs (SerpAPI/Bing).
- **LinkedIn is never scraped** — pages are auth-walled and their ToS prohibit it. Only public search-engine snippets of indexed profiles are used.
- No authentication bypass, no anti-bot evasion, no private data. Public emails are stored only when explicitly published by the person.

## Tech stack

**Backend** Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Alembic · Pydantic v2 · Celery · Redis · PostgreSQL 16 + pgvector · LangGraph/LangChain · OpenAI/Anthropic SDKs · httpx · BeautifulSoup/trafilatura · Playwright (optional)
**Frontend** Next.js 15 · React 19 · TypeScript · Tailwind CSS · shadcn/ui-style kit · TanStack Query · Zustand · React Hook Form + Zod · Framer Motion · Recharts · Lucide
**Ops** Docker · docker-compose · Nginx · GitHub Actions · structlog

## Tests

```
backend:  56 pytest cases (unit, integration, API) — SQLite in-suite,
          migrations validated against real PostgreSQL+pgvector in CI
frontend: vitest + testing-library component/unit tests
e2e:      Playwright drive-through (register → search → results → save → analytics)
```
