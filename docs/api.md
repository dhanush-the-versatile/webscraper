# API Documentation

Base URL: `http://localhost:8080/api/v1` (or `:8000` when running the backend
directly). Interactive OpenAPI docs live at **`/docs`**.

## Conventions

- **Auth**: `Authorization: Bearer <access_token>` on every endpoint except
  `/health`, `/ready`, and the `/auth/*` entry points.
- **Errors**: consistent envelope
  ```json
  { "error": { "code": "not_found", "message": "Candidate not found.", "details": {} } }
  ```
- **Pagination**: `?page=1&page_size=20` → `{ items, total, page, page_size }`.
- **Rate limit**: 240 req/min per client IP on `/api/v1/*` (429 + `Retry-After`).

## Auth

| Method & path | Body | Returns |
|---|---|---|
| `POST /auth/register` | `{email, password, full_name?}` | `201` UserRead |
| `POST /auth/login` | `{email, password}` | `{access_token, refresh_token, token_type}` |
| `POST /auth/refresh` | `{refresh_token}` | new token pair |
| `POST /auth/oauth` | `{provider: "google"\|"github", code, redirect_uri?}` | token pair |
| `GET /auth/me` | – | current user |
| `PATCH /auth/me` | `{full_name?, avatar_url?, password?}` | updated user |

Access tokens live 30 min, refresh tokens 30 days (configurable). Roles:
`admin`, `recruiter` (default), `viewer`.

## Searches

### Start a search

```http
POST /searches
{ "query": "Find senior React developers with TypeScript in Berlin", "max_results": 30 }
```

`202 Accepted` → the pipeline runs in the background (Celery, or inline
fallback). Response is the search record with `status: "pending"`.

### Poll status

```http
GET /searches/{id}
```

`status` walks `pending → understanding → searching → collecting → ranking →
completed | failed`. Once past `searching`, `parsed_requirement` and
`generated_queries` are populated.

### Ranked results

```http
GET /searches/{id}/results?page=1&page_size=50&min_score=60
```

```json
{
  "id": "…", "raw_query": "…", "status": "completed", "result_count": 30,
  "parsed_requirement": { "frameworks": ["react"], "seniority": "senior", … },
  "results": [
    {
      "rank": 1,
      "candidate": { "id": "…", "full_name": "Alex Tanaka", "github_url": "…", … },
      "scores": {
        "overall_score": 88.1, "skill_match": 100.0, "experience_match": 100.0,
        "technology_match": 100.0, "location_match": 100.0,
        "portfolio_score": 45.0, "github_activity_score": 82.4, "relevance_score": 74.0
      },
      "summary": "React Developer at Cloudforge based in Berlin…",
      "explanation": "Overall relevance score: 88/100. Matches required skills: react, typescript…",
      "matched_skills": ["react", "typescript"],
      "missing_skills": []
    }
  ]
}
```

`GET /searches` lists your searches (paginated).

## Candidates

| Method & path | Notes |
|---|---|
| `GET /candidates` | Browse the pool. `q` (query) + `mode` = `keyword` \| `semantic` \| `hybrid`; filters `skills`, `countries`, `cities`, `companies`, `industries`, `technologies` (all repeatable), `min_years_experience`. **keyword** = SQL match; **semantic** = pgvector cosine similarity to the query embedding; **hybrid** = blended keyword-rank + semantic score |
| `GET /candidates/{id}` | Full profile: bio, skills with weights, experiences, GitHub stats, provenance (`sources[]` with URL/snippet/fetched_at), extraction confidence |

## Saved candidates & notes

| Method & path | Body |
|---|---|
| `GET /saved` | – |
| `POST /saved` | `{candidate_id, tags?: string[]}` (409 if already saved) |
| `DELETE /saved/{candidate_id}` | – |
| `POST /notes` | `{candidate_id, body}` |
| `GET /notes/candidate/{candidate_id}` | – |
| `PATCH /notes/{note_id}` | `{body}` |
| `DELETE /notes/{note_id}` | – |

## Exports

```http
POST /exports
{ "search_id": "…", "format": "csv" | "xlsx" | "pdf" | "json" }
```

Streams the file (`Content-Disposition: attachment`). `GET /exports` lists
your export history; `GET /exports/formats` lists supported formats.

## History & analytics

| Method & path | Returns |
|---|---|
| `GET /history` | Paginated activity feed (`search.created`, `candidate.saved`, `export.created`, …) |
| `GET /analytics?days=30` | Dashboard aggregate: totals, searches-over-time series, top skills/countries/technologies, candidates-by-source, score distribution buckets |

## Health

| Path | Purpose |
|---|---|
| `GET /health` | Liveness (no auth) |
| `GET /ready` | Readiness — checks DB connectivity |

## cURL walkthrough

```bash
API=http://localhost:8080/api/v1

# register + login
curl -s $API/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"me@corp.io","password":"s3cretpass","full_name":"Me"}'
TOKEN=$(curl -s $API/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"me@corp.io","password":"s3cretpass"}' | jq -r .access_token)
AUTH="Authorization: Bearer $TOKEN"

# search
SID=$(curl -s -X POST $API/searches -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"query":"Need Python backend developers in Amsterdam"}' | jq -r .id)

# poll until completed
watch -n1 "curl -s $API/searches/$SID -H '$AUTH' | jq -r .status"

# results + export
curl -s "$API/searches/$SID/results" -H "$AUTH" | jq '.results[0]'
curl -s -X POST $API/exports -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"search_id\":\"$SID\",\"format\":\"csv\"}" -o candidates.csv
```
