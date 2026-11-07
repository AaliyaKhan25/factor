"""Business code: random, revocable, optional expiry or single use."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils.time import utcnow


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    single_use: Mapped[bool] = mapped_column(Boolean, default=False)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
