# Proof of Talk AI Matchmaking

Quality-first matchmaking web app built for the Proof of Talk case study.

The system is designed for curated, high-value intros (not mass networking): each attendee gets a small set of high-confidence matches with plain-English reasons.

## What This App Does

- Builds rich attendee profiles from structured and optional external signals
- Generates matches with a strict quality bar:
  - only `score > 65`
  - target `3-7` recommendations per attendee (when available)
- Explains every match in plain language
- Supports intro workflow (request, accept/decline)
- Collects feedback and improves future ranking
- Surfaces strategic scenarios (pair and triad opportunities)
- Provides organizer workflows (add attendees, review/export results)
- Enforces role-based access (organizer vs attendee)

## Tech Stack

- Backend: FastAPI
- Templates/UI: Jinja2 + CSS
- Database: SQLite for local demo, Postgres-ready via `DATABASE_URL`
- Auth: session cookie + CSRF protection + role checks

## Quick Start (Local)

```bash
python -m pip install --user -r requirements.txt
python scripts/seed_data.py
python scripts/generate_level2_artifacts.py
python -m uvicorn app.main:app --reload
```

Open:
- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/login`
- `http://127.0.0.1:8000/organizer`

## Default Demo Credentials

- Organizer:
  - email: `organizer@pot.local`
  - password: `organizer123`
- Attendee:
  - attendee ID: `1` (or any seeded attendee id)
  - passcode: `attendee123-<attendee_id>` (example: `attendee123-1`)

Override with environment variables:
- `ORGANIZER_EMAIL`
- `ORGANIZER_PASSWORD`
- `ATTENDEE_BOOTSTRAP_PASSWORD`
- `AUTH_SECRET`

## Core API Endpoints

- `GET /v1/matches/{attendee_id}`
- `POST /v1/feedback`
- `POST /v1/intros`
- `POST /v1/intros/{intro_id}`
- `GET /v1/scenarios`
- `GET /v1/organizer/metrics`
- `POST /v1/enrich/company`
- `GET /health`

Note:
- API routes require login
- State-changing routes require CSRF token header `X-CSRF-Token`

## Configuration

### Required for production

- `APP_ENV=production`
- `AUTH_SECRET` (strong random secret)
- `ORGANIZER_PASSWORD` (strong password)
- `COOKIE_SECURE=true`
- `FORCE_HTTPS=true`
- `ALLOWED_HOSTS=<your-domain>`
- `DATABASE_URL=<postgres-url>`

### Optional tuning

- `HOME_PAGE_SIZE` (default `80`)
- `ORGANIZER_PAGE_SIZE` (default `100`)
- `SEED_ON_STARTUP=false`

## Security Controls Implemented

- Signed session cookies
- CSRF protection on mutating routes
- Role-based route protection
- Login lockout / brute-force throttling
- Rate limiting
- Secure headers and host validation
- SSRF protections in enrichment logic
- Audit logging for sensitive organizer actions

## Scaling Notes (2,500 Attendees Target)

- Query patterns optimized to avoid per-candidate DB loops
- Candidate hydration batched (no N+1 on match views)
- Scenario generation bounded to avoid combinatorial blowups
- Paginated organizer and attendee list views

Benchmark script:

```bash
python scripts/benchmark_2500.py
```

## Test

```bash
python -m pytest -q
```

## Deployment

### Docker

```bash
cp .env.example .env
docker compose --env-file .env build
docker compose --env-file .env up -d
```

Docs:
- `docs/deployment/Production_Deployment_Runbook.md`
- `docs/deployment/Vercel_Deployment.md`

### Vercel

Entrypoint: `main.py` (exports `app`).

Use managed Postgres in production. Do not rely on local disk for persistent data.

## Repository Layout

- `app/` FastAPI app, services, templates, static assets
- `scripts/` seed/benchmark/generation scripts
- `tests/` automated tests
- `docs/` case study and deployment docs
- `data/seed/` sample attendee seed data

## Submission Artifacts

- Level 1 concept: `docs/Case_Study_3_Submission_Draft.md`
- Level 2 POC: `docs/level2/Proof_of_Concept.md`
- Level 2 wireframe: `docs/level2/wireframe-clickable.html`
- Sample input/output: `docs/level2/sample_input_12_attendees.json`, `docs/level2/sample_output_matches.json`, `docs/level2/sample_output_scenarios.json`

## Local-Only Files (Not for GitHub)

The following are intentionally gitignored:
- `docs/Project_Master_Guide.md`
- `docs/plans/`
- `docs/local/` (if used)

