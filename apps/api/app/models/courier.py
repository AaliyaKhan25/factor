"""Seller-configured courier adapters and order tracking state."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils.time import utcnow


class CourierConnection(Base):
    __tablename__ = "courier_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(40), default="generic")
    credentials_encrypted: Mapped[str] = mapped_column(String(4000), default="")
    webhook_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    webhook_secret_encrypted: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CourierShipment(Base):
    __tablename__ = "courier_shipments"
    __table_args__ = (UniqueConstraint("order_id", name="uq_courier_shipment_order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    courier_connection_id: Mapped[int | None] = mapped_column(ForeignKey("courier_connections.id"), nullable=True)
    courier_name: Mapped[str] = mapped_column(String(100))
    awb: Mapped[str] = mapped_column(String(100), index=True)
    tracking_url: Mapped[str] = mapped_column(String(1000), default="")
    status: Mapped[str] = mapped_column(String(32), default="label_created")
    status_detail: Mapped[str] = mapped_column(String(300), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class CourierWebhookEvent(Base):
    __tablename__ = "courier_webhook_events"
    __table_args__ = (UniqueConstraint("connection_id", "event_id", name="uq_courier_event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("courier_connections.id"), index=True)
    event_id: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
