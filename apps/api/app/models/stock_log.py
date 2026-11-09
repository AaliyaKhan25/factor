"""Append-only stock movements for a ready-stock catalog item."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils.time import utcnow


class StockLog(Base):
    __tablename__ = "stock_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    catalog_item_id: Mapped[int] = mapped_column(ForeignKey("catalog_items.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # opening, restock, sale, cancellation, count
    quantity_delta: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(String(240), default="")
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
