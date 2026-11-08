"""Something the seller sells: ready stock, or made to order with a limit on open orders."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils.time import utcnow


class CatalogItem(Base):
    __tablename__ = "catalog_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    # ready_stock | made_to_order
    kind: Mapped[str] = mapped_column(String(16))
    price_paise: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)   # ready stock: units left
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)   # made to order: open orders at once
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
