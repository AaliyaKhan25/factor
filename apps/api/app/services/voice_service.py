"""Rule based voice command parser and one time, session bound proposals."""
import hashlib
import re
import secrets
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.activity_log import ActivityLog
from ..models.catalog_item import CatalogItem
from ..models.conversation import Conversation
from ..models.message import Message
from ..models.stock_log import StockLog
from ..models.voice_proposal import VoiceProposal
from ..schemas.orders import CustomerIn, LineIn, OrderCreate
from ..services import activity_service, conversation_service, inventory_service
from ..utils.time import utcnow


def _log(db: Session, business_id: int, actor_id: int, action: str, detail: str = "") -> None:
    activity_service.log(db, business_id=business_id, actor_user_id=actor_id,
                          action=f"voice.{action}", entity="voice", detail=detail)


def _proposal(db: Session, business_id: int, actor_id: int, session_id: str, action: str, payload: dict, summary: str) -> dict:
    token = secrets.token_urlsafe(32)
    row = VoiceProposal(token_hash=hashlib.sha256(token.encode()).hexdigest(), business_id=business_id,
                        actor_user_id=actor_id, session_id=session_id, action=action, payload=payload, summary=summary,
                        expires_at=utcnow() + timedelta(minutes=2))
    db.add(row)
    _log(db, business_id, actor_id, "propose", summary)
    db.commit()
    return {"type": "proposal", "token": token, "action": action, "summary": summary,
            "expires_at": row.expires_at, "voice_confirmation_allowed": action == "send_reply"}


def process_command(db: Session, business_id: int, actor_id: int, session_id: str, command: str) -> dict:
    text = " ".join(command.strip().split())
    if not text:
        raise HTTPException(status_code=422, detail="No voice command was recognized")
    low = text.casefold()
    if re.search(r"\b(read|show|tell me)\b.*\b(today'?s|today)\b.*\b(dm|message|inbox)s?\b", low):
        rows = db.scalars(select(Conversation).where(Conversation.business_id == business_id,
            Conversation.last_message_at >= utcnow().replace(hour=0, minute=0, second=0, microsecond=0))
            .order_by(Conversation.last_message_at.desc()).limit(20)).all()
        summary = "No DMs today." if not rows else f"You have {len(rows)} chats updated today. " + "; ".join(
            f"{c.display_name}: {c.last_preview}" for c in rows[:5])
        _log(db, business_id, actor_id, "read", "today's DMs")
        db.commit()
        return {"type": "read_only", "text": summary}
    if re.search(r"\b(read|show|tell me)\b.*\blow stock\b", low):
        items = db.scalars(select(CatalogItem).where(CatalogItem.business_id == business_id,
            CatalogItem.active.is_(True), CatalogItem.kind == "ready_stock", CatalogItem.quantity <= inventory_service.LOW_STOCK_AT)
            .order_by(CatalogItem.quantity, CatalogItem.name)).all()
        summary = "No items are low on stock." if not items else "Low stock: " + "; ".join(
            f"{item.name}, {item.quantity or 0} left" for item in items)
        _log(db, business_id, actor_id, "read", "low stock")
        db.commit()
        return {"type": "read_only", "text": summary}
    match = re.search(r"\b(?:restock|add stock)\s+(\d+)\s+(?:to\s+)?(.+)$", text, re.I)
    if match:
        qty, name = int(match.group(1)), match.group(2).strip(" .")
        item = db.scalar(select(CatalogItem).where(CatalogItem.business_id == business_id,
            func.lower(CatalogItem.name) == name.casefold(), CatalogItem.kind == "ready_stock", CatalogItem.active.is_(True)))
        if item is None or qty < 1:
            raise HTTPException(status_code=422, detail="I could not match that ready stock item and quantity")
        return _proposal(db, business_id, actor_id, session_id, "restock", {"item_id": item.id, "quantity": qty},
                         f"Add {qty} to {item.name} (current stock {item.quantity or 0})")
    match = re.search(r"\b(?:reply|send reply)\s+(?:to\s+)?(?:chat\s+)?(\d+)\s+(?:saying|with)\s+(.+)$", text, re.I)
    if match:
        conv_id, reply = int(match.group(1)), match.group(2).strip(" \"'")
        conv = db.get(Conversation, conv_id)
        if conv is None or conv.business_id != business_id or not reply:
            raise HTTPException(status_code=404, detail="Chat or reply not found")
        return _proposal(db, business_id, actor_id, session_id, "send_reply", {"conversation_id": conv.id, "text": reply[:1000]},
                         f"Reply to {conv.display_name}: {reply[:180]}")
    if re.search(r"\b(?:bought|ordered|purchased|khareede|ne liye)\b", low):
        from ..ai.extractor import parse_voice_order
        parsed = parse_voice_order(text)
        customer = parsed["customer"]
        lines = []
        names = []
        for draft in parsed["items"]:
            name = draft["name"].strip()
            item = db.scalar(select(CatalogItem).where(CatalogItem.business_id == business_id,
                func.lower(CatalogItem.name) == name.casefold(), CatalogItem.active.is_(True)))
            if item is None:
                raise HTTPException(status_code=422, detail=f"Could not find ‘{name}’ in the active catalog")
            lines.append({"catalog_item_id": item.id, "quantity": int(draft["quantity"])})
            names.append(f"{draft['quantity']} × {item.name}")
        if not lines:
            raise HTTPException(status_code=422, detail="Could not identify order items")
        payload = {"customer": {"name": customer["name"], "phone": customer.get("phone"),
                                "handle": customer.get("handle")}, "items": lines, "transcript": text[:400]}
        return _proposal(db, business_id, actor_id, session_id, "create_order", payload,
                         f"Create order for {customer['name']}: {', '.join(names)}. Prices will come from your catalog.")
    _log(db, business_id, actor_id, "unmatched", text[:200])
    db.commit()
    return {"type": "needs_clarification", "text": "Try ‘read today’s DMs’, ‘read low stock’, ‘restock 4 to [item]’, or ‘reply to chat [number] saying [message]’."}


def confirm_proposal(db: Session, business_id: int, actor_id: int, session_id: str, token: str,
                     *, voice_phrase: str | None = None) -> dict:
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = db.scalar(select(VoiceProposal).where(VoiceProposal.token_hash == digest).with_for_update())
    if row is None or row.business_id != business_id or row.actor_user_id != actor_id or row.session_id != session_id:
        raise HTTPException(status_code=404, detail="Confirmation proposal not found")
    if row.consumed_at is not None:
        raise HTTPException(status_code=410, detail="This proposal was already used")
    if row.expires_at <= utcnow():
        _log(db, business_id, actor_id, "expire", row.summary)
        db.commit()
        raise HTTPException(status_code=410, detail="This proposal has expired")
    if voice_phrase is not None:
        if row.action != "send_reply" or voice_phrase.casefold().strip() not in {"yes", "send", "haan", "ha", "bhej do"}:
            raise HTTPException(status_code=403, detail="This action needs tap confirmation")
    if row.action == "restock":
        item = db.get(CatalogItem, row.payload["item_id"])
        if item is None or item.business_id != business_id:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        inventory_service.restock(db, item, row.payload["quantity"], actor_id, "Confirmed by voice")
        from .sheet_sync_service import enqueue_sync
        enqueue_sync(db, business_id)
        result = {"type": "completed", "text": f"Added {row.payload['quantity']} to {item.name}.", "item_id": item.id}
    elif row.action == "send_reply":
        conv = db.get(Conversation, row.payload["conversation_id"])
        if conv is None or conv.business_id != business_id:
            raise HTTPException(status_code=404, detail="Chat not found")
        conversation_service.add_message(db, conv, "out", "owner", row.payload["text"])
        result = {"type": "completed", "text": "Reply saved to the chat.", "conversation_id": conv.id}
    elif row.action == "create_order":
        from ..services import order_service
        payload = row.payload
        order = order_service.create_order(db, business_id, actor_id, OrderCreate(
            customer=CustomerIn(**payload["customer"]), source="voice",
            items=[LineIn(**line) for line in payload["items"]],
            note=f"Voice order: {payload['transcript']}",
        ))
        activity_service.log(db, business_id=business_id, actor_user_id=actor_id,
                             action="order.voice_create", entity="order", entity_id=order.id,
                             detail=payload["transcript"])
        from .sheet_sync_service import enqueue_sync
        enqueue_sync(db, business_id)
        result = {"type": "completed", "text": f"Order {order.code} was created.", "order_id": order.id, "order_code": order.code}
    else:
        raise HTTPException(status_code=422, detail="Unsupported proposal action")
    row.consumed_at = utcnow()
    _log(db, business_id, actor_id, "confirm", row.summary)
    db.commit()
    return result
