"""Rule based voice command parser and one time, session bound proposals."""
import hashlib
import re
import secrets
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai import voice_text
from ..models.activity_log import ActivityLog
from ..models.catalog_item import CatalogItem
from ..models.conversation import Conversation
from ..models.message import Message
from ..models.order import Order
from ..models.stock_log import StockLog
from ..models.voice_proposal import VoiceProposal
from ..schemas.orders import CustomerIn, LineIn, OrderCreate
from ..services import activity_service, conversation_service, inventory_service, order_service, payment_service
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


HELP_TEXT = ("Try: ‘how many [item] are left’, ‘read low stock’, ‘read today’s DMs’, "
             "‘restock 4 to [item]’, ‘count 12 for [item]’, ‘confirm order ORD-1001’, "
             "or ‘Rahul ordered 2 [item]’.")


def _active_items(db: Session, business_id: int) -> list[CatalogItem]:
    return list(db.scalars(select(CatalogItem).where(CatalogItem.business_id == business_id,
                                                      CatalogItem.active.is_(True)).order_by(CatalogItem.id)).all())


def _stock_line(db: Session, item: CatalogItem) -> str:
    if item.kind == "ready_stock":
        qty = item.quantity or 0
        return f"{item.name}: {qty} left." + (" That is low." if qty <= inventory_service.LOW_STOCK_AT else "")
    from . import order_service
    return f"{item.name}: {order_service.availability(db, item)} of {item.capacity} order slots free."


def _read(db: Session, business_id: int, actor_id: int, what: str, text: str) -> dict:
    _log(db, business_id, actor_id, "read", what)
    db.commit()
    return {"type": "read_only", "text": text}


def process_command(db: Session, business_id: int, actor_id: int, session_id: str, command: str) -> dict:
    raw = " ".join(command.strip().split())
    if not raw:
        raise HTTPException(status_code=422, detail="No voice command was recognized")
    # Speech to text may send Hindi script, Hinglish or number words. Match on cleaned Latin text.
    text = voice_text.numberize(voice_text.to_latin(raw))
    low = text.casefold()
    items = _active_items(db, business_id)
    mentioned = voice_text.find_items(low, items)

    # 1. Reply: the message itself is taken from the original words, never rewritten.
    match = re.search(r"\b(?:reply|send reply)\s+(?:to\s+)?(?:chat\s+)?(\w+)\s+(?:saying|with)\s+(.+)$", raw, re.I)
    number = voice_text.word_to_int(match.group(1)) if match else None
    if match and number is not None:
        reply = match.group(2).strip(" \"'")
        conv = db.get(Conversation, number)
        if conv is None or conv.business_id != business_id or not reply:
            raise HTTPException(status_code=404, detail="Chat or reply not found")
        return _proposal(db, business_id, actor_id, session_id, "send_reply", {"conversation_id": conv.id, "text": reply[:1000]},
                         f"Reply to {conv.display_name}: {reply[:180]}")

    # Order pipeline actions are proposals too; cancellation can never happen from an unreviewed transcript.
    status_command = re.search(
        r"\b(confirm|pack|mark|ship|deliver|cancel|confirm\s+the|pack\s+the|ship\s+the|cancel\s+the)\s+(?:the\s+)?order\s+(ord[- ]?\d+)\b"
        r"|\border\s+(ord[- ]?\d+)\s+(?:as\s+)?(confirmed|packed|shipped|delivered|cancelled|canceled)\b", low)
    if status_command:
        code = (status_command.group(2) or status_command.group(3)).replace(" ", "").upper()
        verb = status_command.group(1) or status_command.group(4)
        target = {"confirm": "confirmed", "confirmed": "confirmed", "pack": "packed", "packed": "packed",
                  "mark": None, "ship": "shipped", "shipped": "shipped", "deliver": "delivered",
                  "delivered": "delivered", "cancel": "cancelled", "cancelled": "cancelled", "canceled": "cancelled"}.get(verb)
        if target is None and verb == "mark":
            tail = low[status_command.end():]
            target = next((s for s in ("confirmed", "packed", "shipped", "delivered", "cancelled", "canceled") if s in tail), None)
            if target == "canceled": target = "cancelled"
        order = db.scalar(select(Order).where(Order.business_id == business_id, Order.code == code))
        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {code} was not found")
        if target is None or target not in order_service.TRANSITIONS[order.status]:
            allowed = ", ".join(order_service.TRANSITIONS[order.status]) or "none"
            raise HTTPException(status_code=409, detail=f"Order {code} is {order.status}; allowed next steps: {allowed}")
        return _proposal(db, business_id, actor_id, session_id, "order_status",
                         {"order_id": order.id, "status": target}, f"Mark order {code} as {target}")

    # Physical count: support both imperative and spoken past-tense forms.
    count_match = re.search(r"\b(?:count|counted|stock count|ginti)\s+(\d{1,6})\b", low)
    if count_match or ("ginti" in low and re.search(r"\d{1,6}", low)):
        qty = int(count_match.group(1)) if count_match else int(re.search(r"\d{1,6}", low).group(0))
        if len(mentioned) != 1 or mentioned[0].kind != "ready_stock":
            raise HTTPException(status_code=422, detail="Say ‘count [quantity] for [ready stock item]’ so I can identify one item")
        item = mentioned[0]
        return _proposal(db, business_id, actor_id, session_id, "stock_count", {"item_id": item.id, "quantity": qty},
                         f"Set {item.name} stock to {qty} (currently {item.quantity or 0})")

    # 2. Restock: a verb, a number and an item.
    qty_match = re.search(r"\b(\d{1,6})\b", low) or re.search(r"\b(do)\b(?=.*\b(?:add|jodo|jod|restock)\b)", low)
    if re.search(r"\b(restock|add stock|add|received|stock up|jodo|jod do|badhao)\b", low) and qty_match:
        qty = 2 if qty_match.group(1) == "do" else int(qty_match.group(1))
        if len(mentioned) != 1 or mentioned[0].kind != "ready_stock" or qty < 1:
            raise HTTPException(status_code=422, detail="I could not match that ready stock item and quantity")
        item = mentioned[0]
        return _proposal(db, business_id, actor_id, session_id, "restock", {"item_id": item.id, "quantity": qty},
                         f"Add {qty} to {item.name} (current stock {item.quantity or 0})")

    # 3. Voice order: "rahul bought 80 roses, total 1600"
    if re.search(r"\b(?:bought|ordered|purchased|khareede|ne liye)\b", low):
        from ..ai.extractor import parse_voice_order
        parsed = parse_voice_order(text)
        customer = parsed["customer"]
        lines = []
        names = []
        for draft in parsed["items"]:
            name = draft["name"].strip()
            found = voice_text.find_items(name, items)
            item = found[0] if len(found) == 1 else next((i for i in items if i.name.casefold() == name.casefold()), None)
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

    # 4. Low stock
    if re.search(r"\blow\b.*\bstock\b|\bstock\b.*\blow\b|running low|\bkam stock\b|\bstock kam\b|\bkya kam\b", low):
        low_items = [i for i in items if i.kind == "ready_stock" and (i.quantity or 0) <= inventory_service.LOW_STOCK_AT]
        low_items.sort(key=lambda i: (i.quantity or 0, i.name))
        summary = "No items are low on stock." if not low_items else "Low stock: " + "; ".join(
            f"{i.name}, {i.quantity or 0} left" for i in low_items)
        return _read(db, business_id, actor_id, "low stock", summary)

    # 5. Today's DMs
    if re.search(r"\b(dms?|messages?|inbox|chats?)\b", low) and re.search(r"\b(read|show|tell|check|any|new|today|todays|aaj)\b", low):
        rows = db.scalars(select(Conversation).where(Conversation.business_id == business_id,
            Conversation.last_message_at >= utcnow().replace(hour=0, minute=0, second=0, microsecond=0))
            .order_by(Conversation.last_message_at.desc()).limit(20)).all()
        summary = "No DMs today." if not rows else f"You have {len(rows)} chats updated today. " + "; ".join(
            f"{c.display_name}: {c.last_preview}" for c in rows[:5])
        return _read(db, business_id, actor_id, "today's DMs", summary)

    # 6. "How many roses are left?" and the Hinglish forms
    asks_stock = re.search(r"\b(how many|how much|kitne|kitna|kitni|stock|left|bache|bacha|bachi|remaining|available|in stock|do i have|hai kya|inventory)\b", low)
    if asks_stock:
        if mentioned:
            return _read(db, business_id, actor_id, "stock question", " ".join(_stock_line(db, i) for i in mentioned[:5]))
        if re.search(r"\b(all|everything|overall|inventory|my stock)\b", low):
            ready = [i for i in items if i.kind == "ready_stock"][:8]
            summary = "No ready-stock items yet." if not ready else "Stock: " + "; ".join(f"{i.name} {i.quantity or 0}" for i in ready)
            return _read(db, business_id, actor_id, "stock overview", summary)
        names = ", ".join(i.name for i in items[:8]) or "none yet"
        _log(db, business_id, actor_id, "unmatched", raw[:200])
        db.commit()
        return {"type": "needs_clarification", "text": f"Which item do you mean? Your items: {names}."}

    _log(db, business_id, actor_id, "unmatched", raw[:200])
    db.commit()
    return {"type": "needs_clarification", "text": HELP_TEXT}


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
    elif row.action == "stock_count":
        item = db.get(CatalogItem, row.payload["item_id"])
        if item is None or item.business_id != business_id:
            raise HTTPException(status_code=404, detail="Inventory item not found")
        inventory_service.count(db, item, row.payload["quantity"], actor_id, "Stock count confirmed by voice")
        from .sheet_sync_service import enqueue_sync
        enqueue_sync(db, business_id)
        result = {"type": "completed", "text": f"Counted {item.name}: now {row.payload['quantity']}.", "item_id": item.id}
    elif row.action == "order_status":
        order = db.get(Order, row.payload["order_id"])
        if order is None or order.business_id != business_id:
            raise HTTPException(status_code=404, detail="Order not found")
        order_service.change_status(db, order, row.payload["status"], actor_id)
        activity_service.log(db, business_id=business_id, actor_user_id=actor_id, action="order.status",
                             entity="order", entity_id=order.id, detail=row.payload["status"])
        from .sheet_sync_service import enqueue_sync
        enqueue_sync(db, business_id)
        result = {"type": "completed", "text": f"Order {order.code} marked {order.status}.", "order_id": order.id}
    elif row.action == "send_reply":
        conv = db.get(Conversation, row.payload["conversation_id"])
        if conv is None or conv.business_id != business_id:
            raise HTTPException(status_code=404, detail="Chat not found")
        conversation_service.add_message(db, conv, "out", "owner", row.payload["text"])
        result = {"type": "completed", "text": "Reply saved to the chat.", "conversation_id": conv.id}
    elif row.action == "create_order":
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
    if row.action == "order_status" and row.payload["status"] == "confirmed":
        order = db.get(Order, row.payload["order_id"])
        result["payment_delivery"] = payment_service.notify_customer(db, order)
        result["text"] += " " + result["payment_delivery"]["message"]
    return result
