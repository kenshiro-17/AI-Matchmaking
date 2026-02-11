# Vercel Deployment Guide

## Goal
Deploy this FastAPI web app to Vercel with persistent production data and secure runtime settings.

## Architecture Notes
- FastAPI app instance is exported via `/main.py`.
- For Vercel serverless runtime, filesystem is ephemeral.
- Persistent production storage must use external database (`DATABASE_URL`).

## Pre-Deploy Checklist
1. Local verification:
   - `python scripts/seed_data.py`
   - `python scripts/generate_level2_artifacts.py`
   - `python -m pytest -q`
2. Ensure `.python-version` is present (`3.12`).
3. Ensure `main.py` exists at repo root.
4. Ensure no secrets are committed.

## Vercel Setup
1. Push repo to GitHub.
2. In Vercel dashboard, create project from this repo.
3. Set environment variables:
   - `APP_ENV=production`
   - `AUTH_SECRET=<strong-random-secret>`
   - `ORGANIZER_EMAIL=<organizer-email>`
   - `ORGANIZER_PASSWORD=<strong-password>`
   - `ATTENDEE_BOOTSTRAP_PASSWORD=<strong-password>`
   - `COOKIE_SECURE=true`
   - `FORCE_HTTPS=true`
   - `TRUST_PROXY_HEADERS=true`
   - `ALLOWED_HOSTS=<your-domain>,*.vercel.app`
   - `DATABASE_URL=<managed-postgres-url>`
   - `SEED_ON_STARTUP=false`
4. Deploy.

## Optional Demo Mode (No External DB)
If you only need a temporary demo:
- omit `DATABASE_URL`
- set `SEED_ON_STARTUP=true`

Behavior:
- app uses SQLite at `/tmp/matchmaking.db` on Vercel
- data can reset between cold starts/redeploys

## Post-Deploy Verification
1. Open `/health` and confirm `{"status":"ok"}`.
2. Open `/login`.
3. Login as organizer.
4. Check `/organizer` and `/v1/organizer/metrics`.
5. Validate attendee page and match API.

## Rollback
If issues appear:
1. Redeploy previous successful deployment in Vercel dashboard.
2. Confirm `/health`, `/login`, and organizer flow.
3. Investigate logs before re-promoting.
