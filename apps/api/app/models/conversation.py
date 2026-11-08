"""A chat thread with one customer on one channel, and who is handling it."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from ..utils.time import utcnow


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("business_id", "channel", "handle", name="uq_conversation_channel_handle"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    channel: Mapped[str] = mapped_column(String(16))            # instagram | whatsapp
    handle: Mapped[str] = mapped_column(String(120))            # @name, phone or platform id
    display_name: Mapped[str] = mapped_column(String(120))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    # agent: the assistant is handling it | needs_owner: waiting for you | resolved: done
    status: Mapped[str] = mapped_column(String(16), default="agent", index=True)
    reason: Mapped[str] = mapped_column(String(200), default="")
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    last_preview: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
