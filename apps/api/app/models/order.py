"""An order and its status pipeline."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils.time import utcnow


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("business_id", "code", name="uq_order_business_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    code: Mapped[str] = mapped_column(String(16))          # ORD-1001, per business
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")   # instagram | whatsapp | manual
    # new | confirmed | packed | shipped | delivered | cancelled
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)
    payment_status: Mapped[str] = mapped_column(String(16), default="unpaid")
    total_paise: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
