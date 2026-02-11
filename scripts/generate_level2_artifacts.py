import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.models import Attendee
from app.services.matching import build_matches_for_attendee
from app.services.scenarios import strategic_scenarios


def main():
    out_dir = Path("docs/level2")
    out_dir.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        attendees = db.query(Attendee).order_by(Attendee.id.asc()).all()
        inputs = []
        outputs = []

        for attendee in attendees:
            inputs.append(
                {
                    "id": attendee.id,
                    "name": attendee.name,
                    "role": attendee.role,
                    "company": attendee.company,
                    "primary_goal": attendee.primary_goal,
                    "secondary_goals": attendee.secondary_goals,
                    "availability": attendee.availability,
                }
            )
            matches = build_matches_for_attendee(db, attendee.id, top_n=5)
            outputs.append(
                {
                    "attendee_id": attendee.id,
                    "attendee_name": attendee.name,
                    "matches": [
                        {
                            "candidate_id": m.candidate_id,
                            "score": m.score,
                            "exploration_flag": m.exploration_flag,
                            "reasons": [m.reason_1, m.reason_2, m.reason_3],
                        }
                        for m in matches
                    ],
                }
            )

        (out_dir / "sample_input_12_attendees.json").write_text(
            json.dumps(inputs, indent=2)
        )
        (out_dir / "sample_output_matches.json").write_text(
            json.dumps(outputs, indent=2)
        )
        scenarios = strategic_scenarios(attendees)
        (out_dir / "sample_output_scenarios.json").write_text(
            json.dumps(scenarios, indent=2)
        )
        print(
            f"Wrote {len(inputs)} attendee inputs, {len(outputs)} output sets, and {len(scenarios)} strategic scenarios."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
