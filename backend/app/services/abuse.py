from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import DomainEvent, LicenseActivation
from app.services.events import emit_event


def detect_activation_abuse(db: Session, license_id, device_hash: str) -> bool:
    since = datetime.now(UTC) - timedelta(hours=1)
    recent_count = db.scalar(
        select(func.count(LicenseActivation.id)).where(
            LicenseActivation.license_id == license_id,
            LicenseActivation.created_at >= since,
        )
    )
    repeated_events = db.scalar(
        select(func.count(DomainEvent.id)).where(
            DomainEvent.event_type == "license.validation_failed",
            DomainEvent.created_at >= since,
        )
    )
    suspicious = (recent_count or 0) >= 5 or (repeated_events or 0) >= 20
    if suspicious:
        emit_event(
            db,
            "abuse.detected",
            "license",
            str(license_id),
            {"reason": "activation_or_validation_spike", "device_hash": device_hash},
        )
    return suspicious
