"""A connected Instagram or WhatsApp account. The token in the webhook URL tells us which business a message belongs to."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils.time import utcnow


class ChannelConnection(Base):
    __tablename__ = "channel_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    channel: Mapped[str] = mapped_column(String(16))            # instagram | whatsapp
    label: Mapped[str] = mapped_column(String(120), default="")
    verify_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
