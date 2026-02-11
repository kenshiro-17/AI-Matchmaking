# Level 2 Proof of Concept

## Deliverables
- Concept document: `/docs/Case_Study_3_Submission_Draft.md`
- Clickable wireframe: `/docs/level2/wireframe-clickable.html`
- Working app: `/app`
- Input dataset (12 fictional attendees): `/docs/level2/sample_input_12_attendees.json`
- Output dataset (quality-gated matches): `/docs/level2/sample_output_matches.json`
- Output dataset (pair/triad scenarios): `/docs/level2/sample_output_scenarios.json`

## What the POC proves
- Role-based auth and route scoping are implemented.
- Audit logging exists for sensitive actions.
- Hard constraints are enforced.
- Soft scoring ranks strategic fit.
- Quality gate is enforced (`score > 65`, target 3-7 when available).
- Match explanations are generated.
- Feedback changes future ranking.
- Strategic pair/triad opportunities are surfaced.
- Organizer can input new attendees from UI.
- Organizer can export recommendations as CSV.
- External source retrieval works through company website enrichment endpoint.
  - Note: endpoint requires outbound network/DNS in runtime environment.
- Enterprise hardening controls (RBAC, CSRF, security headers, SSRF guard, audit logs) are implemented.

## Run
```bash
python -m pip install --user -r requirements.txt
python scripts/seed_data.py
python scripts/generate_level2_artifacts.py
python -m uvicorn app.main:app --reload
```

Open:
- App: `http://127.0.0.1:8000`
- Organizer workspace: `http://127.0.0.1:8000/organizer`
- Matches API: `http://127.0.0.1:8000/v1/matches/1`
- Scenarios API: `http://127.0.0.1:8000/v1/scenarios`
- Enrichment API example: `POST /v1/enrich/company?attendee_id=1&source_url=https://example.com`

## 5-minute demo flow
1. Open attendee view and show quality-gated recommendations.
2. Show explanation reasons on match cards.
3. Show organizer strategic scenarios (pair and triad).
4. Submit feedback and refresh ranking.
5. Show organizer metrics.
