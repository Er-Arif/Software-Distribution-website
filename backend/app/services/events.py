from sqlalchemy.orm import Session

from app.db.models import AuditLog, DomainEvent, Notification


def audit(
    db: Session,
    action: str,
    target_type: str,
    actor_id=None,
    target_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=metadata or {},
        )
    )


def emit_event(
    db: Session,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str | None = None,
    payload: dict | None = None,
) -> None:
    db.add(
        DomainEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload or {},
        )
    )


def notify(db: Session, user_id, event_type: str, title: str, body: str, data: dict | None = None) -> None:
    db.add(Notification(user_id=user_id, event_type=event_type, title=title, body=body, data=data or {}))
