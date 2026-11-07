"""Business: name, UPI ID, language, template."""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils.time import utcnow


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    upi_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    template: Mapped[str] = mapped_column(String(32), default="general")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
