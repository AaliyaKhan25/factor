"""Who did what and when (the evidence trail)."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils.time import utcnow


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int | None] = mapped_column(ForeignKey("businesses.id"), nullable=True, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    detail: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
