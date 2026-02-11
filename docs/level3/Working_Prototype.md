# Level 3 Prototype Status and Quality Policy

This working prototype is configured with a strict quality-over-quantity policy:
- Show only matches with `score > 65`.
- Return `3-7` matches when enough candidates pass threshold.
- If fewer than 3 pass, the system shows only qualified matches and flags organizer curation fallback.
- Strategic scenario engine surfaces pair and triad opportunities for concierge intros.

## Current implementation status
- Running web app with attendee view and organizer snapshot.
- Role-based authentication is active (organizer and attendee access paths).
- Per-attendee credential model is active (`attendee123-<id>` for seeded demo accounts).
- API endpoints are role-protected with session auth.
- Audit logs are captured for login, attendee changes, enrichment, intros, feedback, and exports.
- CSRF, rate-limiting, lockout, SSRF protections, and security headers are implemented.
- Match explanations in plain English.
- Feedback submission updates future ranking.
- Generated sample input/output artifacts for 12 fictional attendees.
- Double-opt-in intro workflow is active.
- Organizer can input attendees and export CSV recommendations.
- External source enrichment is available via company website endpoint.
- Containerized deployment assets added (`Dockerfile`, `docker-compose.yml`, `.env.example`).
- Scalability guards added for 2,500-attendee operation:
  - bounded scenario generation,
  - paginated organizer/overview attendee lists,
  - aggregated feedback scoring query,
  - batched candidate hydration for match responses.

## Endpoints
- `GET /v1/matches/{attendee_id}`
- `POST /v1/feedback`
- `POST /v1/intros`
- `POST /v1/intros/{intro_id}`
- `POST /v1/enrich/company`
- `GET /v1/organizer/metrics`
- `GET /v1/scenarios`
- `GET /v1/scenarios?attendee_id=<id>`
- `GET /health`

## UI routes
- `GET /login`
- `GET /` (role-aware landing)
- `GET /attendees/{id}` (attendee workspace, role-scoped)
- `GET /organizer` (organizer workspace)

## Why this improves quality
- Prevents weak “just in case” recommendations.
- Preserves attendee trust in curated intros.
- Keeps meeting calendars focused on high-confidence opportunities.
- Gives organizers explicit pair/triad pathways for high-leverage intros.

Security reference document:
- `/docs/security/Security_Hardening_Plan_and_Implementation.md`
