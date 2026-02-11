# Proof of Talk AI Matchmaking

Quality-first matchmaking web app for curated summit networking.

This system is built for high-stakes events where conversation quality matters more than meeting volume.

## What It Does

- Recommends high-confidence matches only (`score > 65`)
- Targets `3-7` matches per attendee (when available)
- Explains every match in plain English
- Supports intro requests (double opt-in style flow)
- Learns from feedback and outcomes
- Surfaces strategic pair + triad opportunities
- Provides organizer console (add/delete attendees, view metrics, export CSV)
- Supports explicit LinkedIn opt-in enrichment (checkbox + profile URL)
- Includes role-based authentication and security controls

## Latest Updates

- Premium UI polish with lightweight motion system (`/static/ui.js`)
- Responsive spacing and resize stability fixes across device classes
- Proof of Talk branding integrated with local static logo asset
- Favicon added for browser tabs (`/static/brand/favicon.svg`)
- GZip response compression enabled
- Live cross-viewport QA done (mobile, tablet, laptop, desktop, big monitor)

## Tech Stack

- FastAPI
- Jinja2 templates + CSS
- SQLAlchemy
- SQLite for local/demo
- Postgres-ready via `DATABASE_URL`

## Quick Start (New Machine)

### 1) Prerequisites

- Python `3.12`
- `pip`
- Git

Optional:
- Docker + Docker Compose

### 2) Clone

```bash
git clone https://github.com/kenshiro-17/AI-Matchmaking.git
cd AI-Matchmaking
```

### 3) Create and activate virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 4) Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 5) Configure environment

```bash
cp .env.example .env
```

For local dev, you can keep defaults and run seeded demo data.

### 6) Seed demo data and start app

```bash
python scripts/seed_data.py
python scripts/generate_level2_artifacts.py
python -m uvicorn app.main:app --reload
```

Open:
- `http://127.0.0.1:8000/login`
- `http://127.0.0.1:8000/organizer`

## Default Demo Credentials

- Organizer:
  - email: `organizer@pot.local`
  - password: `organizer123`
- Attendee:
  - attendee ID: `1` (or any seeded attendee ID)
  - passcode: `attendee123-<attendee_id>` (example: `attendee123-1`)

## Local Verification

```bash
python -m pytest -q
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## API Endpoints

- `GET /v1/matches/{attendee_id}`
- `POST /v1/feedback`
- `POST /v1/intros`
- `POST /v1/intros/{intro_id}`
- `GET /v1/scenarios`
- `GET /v1/organizer/metrics`
- `POST /v1/enrich/company`
- `POST /v1/enrich/linkedin`
- `GET /health`

Notes:
- API routes require authenticated session
- State-changing routes require CSRF token (`X-CSRF-Token`)

## Security Controls

- Signed auth cookies
- CSRF validation
- Role-based access control (organizer vs attendee)
- Login lockout and rate limiting
- Secure headers and host checks
- SSRF protection for enrichment source URLs
- LinkedIn enrichment requires explicit attendee opt-in + profile URL
- Organizer attendee deletion requires explicit typed-name confirmation
- Audit logging for sensitive actions

## Performance and Scale Notes

- Query optimization to avoid per-candidate feedback DB loops
- Batched candidate hydration (avoids N+1 patterns)
- Bounded scenario generation (prevents combinatorial blowups)
- Pagination on attendee-heavy views
- GZip middleware enabled
- Synthetic benchmark script for 2,500 attendees:

```bash
python scripts/benchmark_2500.py
```

## Docker Run

```bash
cp .env.example .env
docker compose --env-file .env build
docker compose --env-file .env up -d
```

## Deploy on Vercel

This repo includes `vercel.json` and `main.py` entrypoint (`app` export).

Required production env vars:

- `APP_ENV=production`
- `DATABASE_URL=<managed-postgres-url>`
- `AUTH_SECRET=<strong-random-secret>`
- `ORGANIZER_EMAIL=<email>`
- `ORGANIZER_PASSWORD=<strong-password>`
- `ATTENDEE_BOOTSTRAP_PASSWORD=<strong-password>`
- `COOKIE_SECURE=true`
- `FORCE_HTTPS=true`
- `TRUST_PROXY_HEADERS=true`
- `ALLOWED_HOSTS=<your-domain>,*.vercel.app`
- `SEED_ON_STARTUP=false`

Detailed guide:
- `docs/deployment/Vercel_Deployment.md`

## Project Structure

- `app/` application code (routes, services, templates, static files)
- `scripts/` seed, benchmark, and artifact generation scripts
- `tests/` automated tests
- `docs/` case-study and deployment docs
- `data/seed/` sample attendee seed dataset

## Submission Artifacts

- Level 1 concept: `docs/Case_Study_3_Submission_Draft.md`
- Level 2 POC: `docs/level2/Proof_of_Concept.md`
- Level 2 wireframe: `docs/level2/wireframe-clickable.html`
- Sample input/output: `docs/level2/sample_input_12_attendees.json`, `docs/level2/sample_output_matches.json`, `docs/level2/sample_output_scenarios.json`
