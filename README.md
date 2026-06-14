# Outflow backend

A production-hardened FastAPI backend that mirrors the moneyprinter.me pipeline.
**Step 1 works out of the box**; steps 2–4 return mock/simulated data until you add
API keys. Ships with auth, env-driven config, structured logging, request IDs,
rate limiting, global error handling, DB persistence, Docker, and tests.

## Quick start

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional — works with no keys
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs (interactive Swagger UI).

## Try it

```bash
# Step 1 — analyze a real website (WORKS with no keys)
curl -X POST localhost:8000/analyze -H 'content-type: application/json' \
  -d '{"url":"https://stripe.com"}'

# Step 2 — find buyers (mock leads)
curl -X POST localhost:8000/leads/find -H 'content-type: application/json' \
  -d '{"icp":{"titles":["VP Sales"]},"limit":3}'

# Step 3 — generate outreach copy
curl -X POST localhost:8000/outreach/generate -H 'content-type: application/json' \
  -d '{"profile":{"url":"x","product":"Outflow"},"lead":{"name":"Dana Lee","title":"VP Sales","company":"Cascade"},"channel":"email"}'

# Step 4 — simulated dial
curl -X POST localhost:8000/dial -H 'content-type: application/json' \
  -d '{"lead":{"name":"Dana Lee","title":"VP Sales","company":"Cascade"}}'
```

## Database + migrations

Models live in `app/models.py`; migrations in `migrations/`. Works with Postgres or,
for zero-setup local dev, sqlite.

```bash
# Local sqlite (no Postgres needed):
export DATABASE_URL="sqlite:///./dev.db"
alembic upgrade head        # creates all tables from migrations/versions/0001_initial.py

# After changing models, autogenerate the next migration:
alembic revision --autogenerate -m "add column x"
alembic upgrade head
```

With Postgres, set `DATABASE_URL=postgresql://user:pass@host:5432/outflow` in `.env`
and run the same `alembic upgrade head`.

## Deploy to the cloud

See **`DEPLOY.md`** for a full Render walkthrough (one-click via `render.yaml`:
API + Postgres + Redis, migrations run automatically). Each feature is unlocked by its
own env var — deploy with just `ANTHROPIC_API_KEY` and add Apollo/Instantly/Twilio later.

## Run with Docker (api + Postgres + Redis)

```bash
cd backend
docker compose up --build
```

The container runs `alembic upgrade head` automatically (see `entrypoint.sh`), then
serves via gunicorn + uvicorn workers. API on http://localhost:8000.

## Authentication

Set `API_KEYS` (comma-separated) to require auth on all step endpoints. Clients send:

```bash
curl -X POST localhost:8000/leads/find \
  -H 'Authorization: Bearer your-secret-key' \
  -H 'content-type: application/json' \
  -d '{"icp":{"titles":["VP Sales"]},"limit":3}'
# X-API-Key: your-secret-key  also works
```

In development with no `API_KEYS`, auth is off for convenience. In `ENVIRONMENT=production`
the app **refuses to boot** unless `API_KEYS` is set, CORS is not `*`, and you're on
Postgres (see `config.validate_for_production`).

## Production checklist

- `ENVIRONMENT=production`, real `API_KEYS`, explicit `CORS_ORIGINS` (no `*`).
- Postgres `DATABASE_URL`; run `alembic upgrade head` on deploy (Docker does this).
- Docs (`/docs`, `/redoc`) auto-disable in production.
- Liveness: `GET /health`. Readiness (checks DB): `GET /ready`.
- Rate limiting is in-memory (single instance). For multiple replicas, move the
  limiter in `observability.py` to Redis (`REDIS_URL` is wired).
- Security headers + request IDs are added on every response.

## Tests

```bash
pytest -q
```

Tests use a file-based sqlite DB and stub the network scraper, so they run offline.
Covers health/readiness, auth on/off, analyze (+persistence), leads, outreach, dial.

## AI content generation

Set **`ANTHROPIC_API_KEY`** (Claude, preferred) or `OPENAI_API_KEY` in `.env`. With a
key present, all generators produce real AI content; with no key they return clean
template/heuristic output so the app still works offline. The provider is reported at
`GET /ready` (`llm_provider`).

```bash
# Per-lead research report
curl -X POST localhost:8000/content/research -H 'content-type: application/json' \
  -d '{"lead":{"name":"Dana Lee","title":"VP Sales","company":"Cascade GTM"}}'

# Social / blog post
curl -X POST localhost:8000/content/social -H 'content-type: application/json' \
  -d '{"profile":{"url":"x","product":"Outflow","value_prop":"Find buyers fast."},"platform":"linkedin"}'

# Call script
curl -X POST localhost:8000/content/script -H 'content-type: application/json' \
  -d '{"lead":{"name":"Dana Lee","title":"VP Sales","company":"Cascade GTM"}}'
```

## What's real vs stubbed

| Endpoint | State | To make it production |
|---|---|---|
| `POST /analyze` | ✅ Working (scrape + heuristic; AI if key set) | Swap httpx→Playwright for SPAs |
| `POST /leads/find` | 🟡 Mock leads | Add `APOLLO_API_KEY`, wire `services/leads.py` |
| `POST /outreach/generate` | ✅ Copy works (AI or template) | Sending stubbed — add Instantly/Smartlead |
| `POST /content/research` | ✅ Working (AI or template) | — |
| `POST /content/social` | ✅ Working (AI or template) | — |
| `POST /content/script` | ✅ Working (AI or template) | — |
| `POST /dial` | 🟡 Simulated | Add Twilio + realtime STT |

## What this scaffold deliberately omits

Database (Postgres), the job queue (Redis/Celery or Temporal), auth, Stripe billing,
webhooks, and email deliverability/warming. Those are described in `../ARCHITECTURE.md`
and `../COSTS.md`. This scaffold is the request/response skeleton you hang them on.

## Layout

```
app/
  main.py            # app factory, middleware, lifespan, /health + /ready
  config.py          # env-driven settings + production validation
  security.py        # API-key auth dependency
  observability.py   # logging, request-id + security headers, rate limiter
  errors.py          # global exception handlers (JSON envelopes)
  db.py              # SQLAlchemy engine/session
  models.py          # ORM models
  crud.py            # persistence helpers
  schemas.py         # pydantic request/response models
  services/
    scraper.py       # step 1a — fetch + clean (WORKS)
    analyzer.py      # step 1b — LLM/heuristic extraction (WORKS)
    leads.py         # step 2 — Apollo integration + mock fallback
    outreach.py      # step 3 — copy gen (WORKS) + send stub
    dialer.py        # step 4 — stub
  routers/           # thin HTTP layer per step (auth-protected)
migrations/          # alembic
tests/               # pytest suite
Dockerfile, docker-compose.yml, entrypoint.sh
```
