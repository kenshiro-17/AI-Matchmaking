import json

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit_log(
    db: Session,
    user: dict | None,
    action: str,
    target_type: str = "",
    target_id: str = "",
    status: str = "success",
    details: dict | None = None,
):
    try:
        actor_role = (user or {}).get("role", "anonymous")
        actor_label = (user or {}).get("label", "")
        row = AuditLog(
            actor_role=actor_role,
            actor_label=actor_label,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else "",
            status=status,
            details=json.dumps(details or {}, separators=(",", ":"), sort_keys=True),
        )
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()
