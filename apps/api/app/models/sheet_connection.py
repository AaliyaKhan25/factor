"""Per-business destination for one-way app-to-Sheets snapshots."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils.time import utcnow


class SheetConnection(Base):
    __tablename__ = "sheet_connections"
    __table_args__ = (UniqueConstraint("business_id", name="uq_sheet_connection_business"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    spreadsheet_id: Mapped[str] = mapped_column(String(128))
    spreadsheet_url: Mapped[str] = mapped_column(String(500))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str] = mapped_column(String(500), default="")
    sync_generation: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
