# Level 2: Wireframe + Proof of Concept

This package includes **everything in Level 1**, plus the required Level 2 artifacts.

## 1) Level 1 Included
- Concept document (2-4 pages): `/docs/Case_Study_3_Submission_Draft.md`

## 2) Clickable Wireframe / UI Mockup
- Figma wireframe: [Proof of Talk Pitch Board v5](https://www.figma.com/online-whiteboard/create-diagram/f832226c-9b28-4c38-be43-8b4ada8f4d64)

## 3) Working Proof of Concept (Core Component)
Core component implemented: **match recommendation engine with explanations**.

### What works
- Takes attendee profile data.
- Applies hard constraints and soft scoring.
- Returns quality-gated recommendations (`score > 65`, target 3-7).
- Provides plain-English reasons per match.

### Live app and endpoint
- Live app: [https://ai-matchmaking-pot.vercel.app](https://ai-matchmaking-pot.vercel.app)
- Core API: `GET /v1/matches/{attendee_id}`

## 4) Sample Input / Output (10-15 Fictional Profiles)
- Sample input (12 attendees): `/docs/level2/sample_input_12_attendees.json`
- Sample output (matches): `/docs/level2/sample_output_matches.json`
- Sample output (scenarios): `/docs/level2/sample_output_scenarios.json`

## 5) Quick Run (Local)
```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/seed_data.py
python scripts/generate_level2_artifacts.py
python -m uvicorn app.main:app --reload
```

Open:
- App: `http://127.0.0.1:8000`
- Organizer: `http://127.0.0.1:8000/organizer`
- Match API example: `http://127.0.0.1:8000/v1/matches/1`
