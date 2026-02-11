# Production Deployment Runbook

## Scope
Deployment guidance for the AI Matchmaking web app using Docker Compose with rollback and verification steps.

## 1) Pre-Deployment
- Confirm code quality:
  - `python scripts/seed_data.py`
  - `python scripts/generate_level2_artifacts.py`
  - `python -m pytest -q`
- Confirm production environment config:
  - copy `.env.example` to `.env`
  - set strong values for `AUTH_SECRET`, `ORGANIZER_PASSWORD`, `ATTENDEE_BOOTSTRAP_PASSWORD`
  - set real `ALLOWED_HOSTS`
  - keep `COOKIE_SECURE=true` and `FORCE_HTTPS=true`
- Confirm backup strategy:
  - backup the persistent volume (`matchmaking_data`) or the underlying DB file.

## 2) Deploy
```bash
docker compose --env-file .env build
docker compose --env-file .env up -d
```

## 3) Verify
- Container status:
  - `docker compose ps`
- Health endpoint:
  - `curl -i http://127.0.0.1:8000/health`
- Critical path checks:
  - login page loads
  - organizer login works
  - `GET /v1/matches/1` works for authenticated session

## 4) Monitor (First 15 Minutes)
- `docker compose logs -f app`
- Watch for:
  - repeated 5xx responses
  - repeated auth failures/lockouts
  - enrichment fetch errors

## 5) Rollback
If deployment introduces critical issues:
1. stop the new container:
   - `docker compose down`
2. restore previous image tag and/or previous DB backup
3. redeploy previous known-good version
4. re-run health + critical-path checks

## 6) Security Notes
- Never commit `.env`.
- Rotate `AUTH_SECRET` and credentials periodically.
- Prefer Postgres in production and run managed backups.
- Keep host/network TLS termination in front of the app.
