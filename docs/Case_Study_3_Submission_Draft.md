# AI-Powered Matchmaking Tool for Proof of Talk

## A) Executive Summary
Proof of Talk wins on conversation quality, not networking volume. In a curated room of senior decision-makers, weak introductions are expensive: they waste scarce meeting slots and reduce trust in the event experience. This proposal delivers a quality-first matchmaking system that recommends who to meet before and during the summit, with clear reasons people can trust. It combines hard constraints, strategic-fit scoring, and limited discovery to avoid echo chambers. It is consent-first: registration is required, enrichment is opt-in. It also surfaces non-obvious opportunities, including pair and triad pathways (for example, founder -> GP -> LP). Output is intentionally constrained to high-confidence results only (score > 65, target 3-7 recommendations when available). The MVP is realistic to ship in weeks and improves during the event through live feedback.

## B) Problem Framing
### Why matchmaking is uniquely hard at Proof of Talk
- Attendees are senior and time-constrained.
- Goals are asymmetric: fundraising, partnerships, regulation, hiring, learning.
- Job titles do not reliably reflect current priorities.
- Bad matches damage trust in a high-curation environment.

### Why simple filtering fails
- Keyword overlap creates generic matches.
- Similarity-only logic misses complementary value.
- Static directories cannot adapt to in-event context changes.

### What success means
- Fewer, higher-confidence introductions.
- Higher “useful meeting” and “follow-up planned” rates.
- Better organizer outcomes: curated tables, stronger intros, measurable business progress.

## C) Users & Personas
### 1) Institutional Investor (Partner/MD)
- Goals: differentiated deal flow, thesis validation.
- Constraints: very limited slots, low tolerance for generic outreach.
- Good match: founder/executive with clear fit, credibility, and timing.

### 2) Founder/CEO
- Goals: capital, strategic distribution, enterprise partnerships.
- Constraints: high opportunity cost per meeting.
- Good match: decision-maker with direct relevance and a realistic next step.

### 3) Bank / Institutional Innovation Executive
- Goals: compliant digital-asset adoption and partner selection.
- Constraints: regulatory and reputational risk.
- Good match: enterprise-ready team with strong compliance posture.

### 4) Infrastructure / Protocol CTO
- Goals: technical partnerships, design partners, selective hiring.
- Constraints: avoids low-depth, non-technical meetings.
- Good match: counterpart with architecture-level complementarity.

## D) Data Strategy
### Sources, value, and risk
1. Registration form (mandatory)
- Value: structured baseline and explicit intent.
- Risk: often shallow.

2. LinkedIn (optional opt-in)
- Value: expertise and trajectory context.
- Risk: privacy sensitivity; stale fields.

3. Company website (optional)
- Value: company strategy and positioning.
- Risk: marketing bias.

4. Public content (optional)
- Value: current thinking and active themes.
- Risk: uneven availability.

5. Past Proof of Talk data (if available)
- Value: strongest context signal for quality.
- Risk: can reinforce old network patterns.

### Mandatory vs optional
- Mandatory: profile basics, goal, availability, exclusions.
- Optional: LinkedIn, website, public content.

### Consent and noisy data handling
- Source-level opt-in.
- Plain-language data use disclosure.
- Attendee controls for edits/exclusions.
- Confidence labels for inferred fields.
- Conservative ranking for low-confidence profiles.

### Cold-start strategy
- 2-minute intent form (seek, offer, constraints).
- Rules-first matching plus organizer curation fallback.

## E) Profile Building Logic
Each attendee is represented by four blocks:
- Identity context (role, authority, language, sector)
- Current focus (what they are actively doing now)
- Seeks (what they want from this event)
- Offers (what value they can provide)

Text signals are interpreted semantically, but structured fields remain the control layer.

Conflict policy:
- Explicit attendee input overrides inferred signals.
- Newer signals outrank older ones.
- Low-confidence inferences are down-weighted.

## F) Matching Logic (Core)
### 1) Hard constraints
- Language compatibility
- Availability overlap
- Exclusions and organizer policy rules

### 2) Soft scoring
- Objective relevance
- Complementarity (investor-founder, bank-infra, policy-operator)
- Decision-level fit
- Asymmetric value exchange
- Feedback prior from observed outcomes

### 3) Exploration / diversity injection
- One limited discovery slot for adjacent high-upside opportunities.
- Discovery still must pass quality threshold.

### 4) Explainability
Each recommendation includes clear reasons, e.g.:
- “Your investment objective aligns with this founder’s active fundraising and institutional traction.”
- “You both have overlapping availability and compatible strategic priorities.”

### 5) Strategic scenario engine (non-obvious opportunities)
- Pair: Kenji’s compliance-focused L2 -> Elena’s bank deployment need.
- Triad: Marcus (founder) -> Aisha (GP) -> Sarah (LP context bridge).

## G) Output & UX Design
### Before event (web-first)
- Show only high-confidence recommendations (`score > 65`).
- Target 3-7 recommendations when enough qualify.
- Match cards include reasons and actions: Request Intro / Save / Not Relevant.

### During event
- Time-aware nudges based on free windows.
- Concierge escalation on mutual accept.

### After event
- Outcome capture: met, follow-up planned, declined.
- Feedback updates future ranking.

Example copy:
“Recommended: Elena Rossi (European Bank). Why: your objective is institutional allocation, and Elena is launching compliant custody while seeking tokenization partners. Shared availability: Day 1 PM.”

## H) Learning & Feedback Loop
- Explicit: rating, outcome, comment.
- Implicit: accept/decline, meeting completion, follow-up behavior.
- Re-rank during event without heavyweight retraining.
- Repeated weak outcomes are penalized or removed.

## I) System Design (Logical, Not Over-Engineered)
### Core components
- Data ingestion
- Profile builder
- Matching service
- Explanation layer
- Scenario engine (pair/triad)
- Notification layer
- Organizer dashboard

### High-level schema
- `attendees`
- `matches`
- `feedback`
- `signals` (optional enrichment traces)

### APIs
- `GET /v1/matches/{attendee_id}`
- `POST /v1/feedback`
- `GET /v1/organizer/metrics`
- `GET /v1/scenarios`

```text
[Ingestion] -> [Profile Builder] -> [Matching + Scenario Engine] -> [Explanations]
                                             |                         |
                                             v                         v
                                       [Organizer Tools]         [Attendee UI]
```

## J) Organizer Perspective
Organizers can use this system to:
- prioritize concierge introductions,
- design better seating and roundtables,
- detect high-value attendees with weak coverage,
- act on pair/triad scenario opportunities.

This strengthens Proof of Talk’s perceived and measurable event value.

## K) Risks, Ethics & Privacy
- Consent-first enrichment; no hidden scraping.
- Transparent “why this match” explanations.
- Anti-spam controls and moderation paths.
- Bias control through exploration and organizer oversight.
- Deliberate non-automation: final intro approval remains human.

## L) MVP Scope & Roadmap
### Level 1 (concept)
- End-to-end design, data strategy, matching logic, UX flow, risks, and roadmap.

### Level 2 (delivered)
- Clickable wireframe.
- Working POC with 12 fictional attendees.
- Generated sample input/output, including strategic scenarios.
- Working web app with attendee workflow + organizer workspace.
- Organizer attendee input form and CSV export for match recommendations.
- External data retrieval from one source (company website enrichment endpoint).
- Production-grade presentation layer improvements:
  - Proof of Talk branding integration (local static logo),
  - browser favicon support,
  - premium UI interactions with lightweight motion,
  - responsive spacing stabilization across mobile/tablet/laptop/desktop/large monitor viewports.

### 90-day roadmap
1. Days 1-30: ingestion, profile builder, hard constraints, quality-gated recommendations.
2. Days 31-60: scoring refinement, explanation quality, feedback loop, organizer metrics.
3. Days 61-90: in-event nudges, scenario tuning, stronger organizer curation workflows.

## Technical Stack
- Web-first UI
- FastAPI backend
- SQLite for MVP (Postgres in production)
- Rule-based scoring + semantic text interpretation + feedback priors
- HTTP enrichment adapter for external source retrieval (company website metadata/content summary)
- Security and runtime hardening:
  - RBAC, CSRF, lockout/rate limiting, audit logs, SSRF controls, secure headers.

## Why this differs from Grip / Brella / Swapcard
- Strict quality gating, not high-volume networking.
- Complementary and strategic-chain logic, not tag similarity only.
- Explainability and organizer-in-the-loop controls as core features.

## How This Scores Against Evaluation Criteria
- Problem Understanding: high-stakes framing, edge cases, quality KPIs.
- System Design: practical architecture, consent model, organizer controls.
- AI & Matching Logic: constraints + scoring + explainability + scenarios.
- Communication: concise, executive-readable, concrete examples.
- Ambition & Execution: Level 1 + Level 2 artifacts + runnable prototype with authenticated organizer tooling, CSV export, external source enrichment, and cross-device UI reliability improvements.

## “Things to Think About” — Direct Answers
1. Cold start: require mini-intent form, rank conservatively, use organizer fallback.
2. Similar vs complementary: prioritize complementary; keep one controlled peer-similarity slot.
3. Quality vs quantity: enforce `score > 65`, target 3-7 recommendations.
4. Privacy/consent: source-level opt-in, transparent use, attendee edit controls.
5. Organizer value: seating, roundtables, concierge intros, coverage monitoring.
6. Feedback loops: explicit + implicit signals drive reranking.
7. Existing tools: differentiate through quality gating, explainability, and triad scenarios.

## Level 2 Package
- Wireframe: `/docs/level2/wireframe-clickable.html`
- POC note: `/docs/level2/Proof_of_Concept.md`
- Input: `/docs/level2/sample_input_12_attendees.json`
- Match output: `/docs/level2/sample_output_matches.json`
- Scenario output: `/docs/level2/sample_output_scenarios.json`
- Working app endpoints include:
- `GET /v1/matches/{attendee_id}`
- `POST /v1/enrich/company`
- `GET /organizer/export/matches.csv`
- `GET /v1/scenarios`
- `GET /favicon.ico` (brand icon support)

## Submission Email Paragraph
I am submitting my case study for an AI-powered matchmaking tool for Proof of Talk. The proposal is quality-first and implementation-focused: consented profile enrichment, explainable matching, strict confidence gating, and feedback-driven adaptation. I also included a Level-2 wireframe and working proof of concept with sample outputs, including non-obvious pair and triad strategic opportunities.

## Evaluation Checklist
| Criteria | Coverage |
|---|---|
| Problem Understanding (30%) | High-stakes framing, edge cases, quality KPIs |
| System Design (25%) | Practical architecture, consent model, organizer controls |
| AI & Matching Logic (25%) | Hard constraints, soft scoring, explainability, scenarios |
| Communication (10%) | Concise, structured, executive-readable narrative |
| Ambition & Execution (10%) | Level 1 + Level 2 artifacts + runnable prototype |
