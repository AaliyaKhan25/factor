"""Write activity log entries."""
from sqlalchemy.orm import Session

from ..models.activity_log import ActivityLog


def log(
    db: Session,
    *,
    business_id: int | None,
    actor_user_id: int | None,
    action: str,
    entity: str,
    entity_id: int | None = None,
    detail: str = "",
) -> None:
    """Add a log row to the current transaction. The caller commits."""
    db.add(
        ActivityLog(
            business_id=business_id,
            actor_user_id=actor_user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=detail[:500],
        )
    )
