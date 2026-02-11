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
- Organizer can delete attendees with typed-name confirmation; related attendee-scoped records are removed in one action.
- External source enrichment is available via company website endpoint.
- LinkedIn enrichment is available with explicit attendee opt-in (checkbox + profile URL).
- Containerized deployment assets added (`Dockerfile`, `docker-compose.yml`, `.env.example`).
- Scalability guards added for 2,500-attendee operation:
  - bounded scenario generation,
  - paginated organizer/overview attendee lists,
  - aggregated feedback scoring query,
  - batched candidate hydration for match responses.
- UI/UX hardening is implemented:
  - Proof of Talk logo served locally under `/static/brand/proof-of-talk-logo.svg`,
  - favicon and `/favicon.ico` route support,
  - premium motion with reduced-motion safe fallback,
  - reveal fallback logic to prevent hidden sections after resize/orientation changes,
  - spacing fixes for Curated Directory and Strategic Scenarios text cards (more generous card padding + improved line-height for readability).
- Cross-device verification executed with Playwright across:
  - iPhone, Android, tablet, laptop, desktop, and big monitor viewports.

## Endpoints
- `GET /v1/matches/{attendee_id}`
- `POST /v1/feedback`
- `POST /v1/intros`
- `POST /v1/intros/{intro_id}`
- `POST /v1/enrich/company`
- `POST /v1/enrich/linkedin`
- `GET /v1/organizer/metrics`
- `GET /v1/scenarios`
- `GET /v1/scenarios?attendee_id=<id>`
- `GET /health`
- `GET /favicon.ico`

## UI routes
- `GET /login`
- `GET /` (role-aware landing)
- `GET /attendees/{id}` (attendee workspace, role-scoped)
- `GET /organizer` (organizer workspace)
- `POST /organizer/attendees/{id}/delete` (organizer-only, CSRF + confirmation gated)

## Demo Credentials
- Organizer email: `organizer@pot.local`
- Organizer password: `organizer123`
- Attendee login ID example: `1`
- Attendee passcode pattern: `attendee123-<attendee_id>` (example: `attendee123-1`)

## Why this improves quality
- Prevents weak “just in case” recommendations.
- Preserves attendee trust in curated intros.
- Keeps meeting calendars focused on high-confidence opportunities.
- Gives organizers explicit pair/triad pathways for high-leverage intros.

Security reference document:
- `/docs/security/Security_Hardening_Plan_and_Implementation.md`

Current deployed URL:
- [https://ai-matchmaking-pot.vercel.app](https://ai-matchmaking-pot.vercel.app)

Primary wireframe (Figma):
- [Proof of Talk Pitch Board](https://www.figma.com/online-whiteboard/create-diagram/f832226c-9b28-4c38-be43-8b4ada8f4d64?utm_source=other&utm_content=edit_in_figjam&oai_id=&request_id=55701c3a-ed32-408d-90b0-bb827b8e79fd)
