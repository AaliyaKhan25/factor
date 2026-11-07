"""A user's membership of a business, with status, role and extra permissions."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils.time import utcnow


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("business_id", "user_id", name="uq_membership_business_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # admin | asset_manager | dept_head | employee
    role: Mapped[str] = mapped_column(String(32), default="employee")
    # pending | active | rejected | removed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    extra_permissions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
