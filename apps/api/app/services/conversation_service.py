"""Receive a customer message, store it, and let the agent answer or hand over to the owner."""
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.conversation import Conversation
from ..models.customer import Customer
from ..models.message import Message
from ..schemas.orders import CustomerIn
from ..utils.time import utcnow
from . import agent_service, order_service


def add_message(db: Session, conv: Conversation, direction: str, sender: str, text: str) -> Message:
    msg = Message(business_id=conv.business_id, conversation_id=conv.id, direction=direction, sender=sender, text=text[:2000])
    db.add(msg)
    conv.last_message_at = utcnow()
    if sender != "agent":          # the list shows what the customer said, not the agent's stock reply
        conv.last_preview = text.replace("\n", " ")[:200]
    db.flush()
    return msg


def _split_contact(channel: str, handle: str) -> tuple[str | None, str | None]:
    digits = re.sub(r"\D", "", handle)
    if channel == "whatsapp" and len(digits) >= 10:
        return digits[-10:], None
    return None, handle


def ingest(db: Session, business_id: int, channel: str, handle: str, name: str, text: str) -> Conversation:
    text = text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Empty message")
    conv = db.scalar(
        select(Conversation).where(
            Conversation.business_id == business_id, Conversation.channel == channel, Conversation.handle == handle
        )
    )
    if conv is None:
        conv = Conversation(business_id=business_id, channel=channel, handle=handle, display_name=name or handle)
        db.add(conv)
        db.flush()
    add_message(db, conv, "in", "customer", text)

    if conv.status == "needs_owner":
        return conv                                  # the owner has it: the agent stays quiet
    if conv.status == "resolved":
        conv.status, conv.reason = "agent", ""

    decision = agent_service.decide(db, conv, text)
    phone, h = _split_contact(channel, handle)

    if decision.order_note:
        order = agent_service.place_order(db, conv, conv.display_name, phone, h, decision.order_note)
        customer = db.get(Customer, order.customer_id)
        conv.customer_id = customer.id
        conv.reason = f"Order {order.code} booked"
        qty, _ = (int(x) for x in decision.order_note.split("|"))
        lines = ", ".join(f"{i.quantity} x {i.name}" for i in _lines(db, order.id))
        add_message(
            db, conv, "out", "agent",
            f"Booked! Your order {order.code}: {lines}, total {agent_service.rupees(order.total_paise)}. "
            "The owner will share payment details shortly.",
        )
        return conv

    if decision.reply:
        add_message(db, conv, "out", "agent", decision.reply)
    if decision.escalate:
        conv.status, conv.reason = "needs_owner", decision.escalate
    if conv.customer_id is None:
        cust = order_service.find_or_create_customer(
            db, business_id, CustomerIn(name=conv.display_name, phone=phone, handle=h)
        )
        conv.customer_id = cust.id
    return conv


def _lines(db: Session, order_id: int):
    from ..models.order_item import OrderItem

    return db.scalars(select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id)).all()
