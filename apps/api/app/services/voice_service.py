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
from ..models.customer import Customer
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
            "expires_at": row.expires_at, "voice_confirmation_allowed": True}


HELP_TEXT = ("You can say: give me a summary. Open orders, inventory, inbox or settings. How many roses are left. "
             "Read low stock. Read today's messages. Take payment from Riya. Restock 4 to roses. Confirm order ORD-1001. "
             "Rahul ordered 2 roses. Reply to chat 3 saying thank you. After I read a change back, say yes to confirm or no to drop it.")


def _active_items(db: Session, business_id: int) -> list[CatalogItem]:
    return list(db.scalars(select(CatalogItem).where(CatalogItem.business_id == business_id,
                                                      CatalogItem.active.is_(True)).order_by(CatalogItem.id)).all())


def _stock_line(db: Session, item: CatalogItem) -> str:
    if item.kind == "ready_stock":
        qty = item.quantity or 0
        return f"{item.name}: {qty} left." + (" That is low." if qty <= inventory_service.LOW_STOCK_AT else "")
    from . import order_service
    return f"{item.name}: {order_service.availability(db, item)} of {item.capacity} order slots free."


def _read(db: Session, business_id: int, actor_id: int, what: str, text: str, **data) -> dict:
    _log(db, business_id, actor_id, "read", what)
    db.commit()
    return {"type": "read_only", "headline": "Here’s what I found", "intent": what, "text": text, **data}


def _item_quantity(text: str, item: CatalogItem) -> int:
    name = r"\s+".join(re.escape(token) for token in re.findall(r"[a-z0-9]+", item.name.casefold()))
    if not name:
        return 1
    count = r"(\d{1,5}|one|two|three|four|five|six|seven|eight|nine|ten|ek|do|teen|char|chaar|paanch|chhe|saat|aath|nau|das|bees|tees|pachees|assi)"
    match = re.search(rf"\b{count}\s*(?:x\s*)?(?:pieces?\s+of\s+|units?\s+of\s+)?{name}(?:s)?\b", text)
    if match:
        return voice_text.word_to_int(match.group(1)) or 1
    match = re.search(rf"\b{name}(?:s)?\s*(?:x|\*)\s*(\d{{1,5}})\b", text)
    return int(match.group(1)) if match else 1



# Where "go to ..." can take the owner. Longer phrases first.
PAGES: list[tuple[str, str, str]] = [
    (r"new order|create order|add order", "/orders/new", "new order"),
    (r"dashboard|daishabord|overview|home|dashbord", "/dashboard", "the overview"),
    (r"inbox|inaboks|messages?|dms?|chats?|sandesh", "/inbox", "the inbox"),
    (r"orders?|ordars?|ordar", "/orders", "orders"),
    (r"catalog|catalogue|kaitalog|products?|items?", "/catalog", "the catalog"),
    (r"inventory|inventri|inventry|stock|stok", "/inventory", "inventory"),
    (r"customers?|kastamars?|kastamar", "/customers", "customers"),
    (r"team|staff|members?", "/setup/team", "the team page"),
    (r"settings?|setings?|sheets?|courier", "/settings", "settings"),
    (r"reports?", "/reports", "reports"),
    (r"payments?", "/payments", "payments"),
    (r"notifications?", "/notifications", "notifications"),
    (r"activity|history", "/activity", "the activity log"),
]
NAV_VERB = r"\b(go to|go|open|take me to|take me|navigate to|navigate|switch to|jao|kholo|khol do|dikhao)\b"


def _navigate(db: Session, business_id: int, actor_id: int, path: str, text: str) -> dict:
    _log(db, business_id, actor_id, "navigate", path)
    db.commit()
    return {"type": "navigate", "path": path, "text": text}


def _briefing(db: Session, business_id: int) -> str:
    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today = db.scalars(select(Order).where(Order.business_id == business_id, Order.created_at >= start)).all()
    live = [o for o in today if o.status != "cancelled"]
    pending = db.scalar(select(func.count(Order.id)).where(Order.business_id == business_id, Order.status == "new")) or 0
    waiting = db.scalar(select(func.count(Conversation.id)).where(Conversation.business_id == business_id,
                                                                  Conversation.status == "needs_owner")) or 0
    low = [i for i in _active_items(db, business_id)
           if i.kind == "ready_stock" and (i.quantity or 0) <= inventory_service.LOW_STOCK_AT]
    parts = [f"Today: {len(live)} orders worth {sum(o.total_paise for o in live) / 100:.0f} rupees.",
             f"{pending} new orders to confirm.", f"{waiting} chats need you."]
    parts.append("Low stock: " + ", ".join(f"{i.name} {i.quantity or 0}" for i in low[:5]) + "." if low else "Stock looks fine.")
    return " ".join(parts)


def process_command(db: Session, business_id: int, actor_id: int, session_id: str, command: str) -> dict:
    raw = " ".join(command.strip().split())
    if not raw:
        raise HTTPException(status_code=422, detail="No voice command was recognized")
    # Speech to text may send Hindi script, Hinglish or number words. Match on cleaned Latin text.
    text = voice_text.numberize(voice_text.to_latin(raw))
    low = text.casefold()
    items = _active_items(db, business_id)
    mentioned = voice_text.find_items(low, items)


    # 0. Help, briefing and screen navigation. Voice must be able to reach every screen.
    if re.search(r"\b(help|what can i say|what can you do|commands)\b", low):
        _log(db, business_id, actor_id, "help", "")
        db.commit()
        return {"type": "read_only", "headline": "What you can say", "intent": "help", "text": HELP_TEXT}
    if re.search(r"\b(briefing|summary|what needs (?:my )?attention|how is (?:my )?business|business today|aaj ka hisab|daily summary)\b", low):
        return _read(db, business_id, actor_id, "briefing", _briefing(db, business_id))
    chat_nav = re.search(NAV_VERB + r"\s+(?:the\s+)?(?:chat|conversation)\s+(\d+)\b", low)
    if chat_nav:
        conv = db.get(Conversation, int(chat_nav.group(2)))
        if conv is None or conv.business_id != business_id:
            raise HTTPException(status_code=404, detail=f"I could not find chat {chat_nav.group(2)}")
        return _navigate(db, business_id, actor_id, f"/inbox/{conv.id}", f"Opening chat with {conv.display_name}.")
    order_nav = re.search(NAV_VERB + r"\s+(?:the\s+)?order\s+(ord[- ]?\d+)\b", low)
    if order_nav:
        code = "ORD-" + re.sub(r"^ORD-?", "", re.sub(r"\s+", "", order_nav.group(2)).upper())
        order = db.scalar(select(Order).where(Order.business_id == business_id, Order.code == code))
        if order is None:
            raise HTTPException(status_code=404, detail=f"I could not find order {code}")
        return _navigate(db, business_id, actor_id, f"/orders/{order.id}", f"Opening {order.code}.")
    if re.search(NAV_VERB, low) and not re.search(r"\b(ord[- ]?\d+|chat \d+)\b", low):
        for pattern, path, label in PAGES:
            if re.search(rf"\b(?:{pattern})\b", low):
                return _navigate(db, business_id, actor_id, path, f"Opening {label}.")
    if re.search(r"\b(go back|back)\b", low):
        return {"type": "navigate", "path": "back", "text": "Going back."}


    # Take payment: "take payment from Riya", "send Riya the QR", "riya se payment lo".
    if re.search(r"\b(payment|pay|qr|paisa|paise|bill|pay ment)\b", low) and re.search(
            r"\b(take|collect|request|ask|send|get|chase|remind|lo|le|maango|mango|maang|bhejo|bhej|do)\b", low):
        customers = list(db.scalars(select(Customer).where(Customer.business_id == business_id)).all())
        words = voice_text._tokens(low)
        named = [c for c in customers if voice_text._tokens(c.name)
                 and all(any(voice_text._same(n, w) for w in words) for n in voice_text._tokens(c.name))]
        code_match = re.search(r"\bord[- ]?(\d+)\b", low)
        if code_match:
            order = db.scalar(select(Order).where(Order.business_id == business_id, Order.code == f"ORD-{code_match.group(1)}"))
        elif named and len({c.name.casefold() for c in named}) == 1:
            # The same person can exist twice (once from a DM, once from an order); use whichever has an unpaid order.
            order = db.scalar(select(Order).where(Order.business_id == business_id, Order.customer_id.in_([c.id for c in named]),
                                                  Order.payment_status != "paid", Order.status != "cancelled")
                              .order_by(Order.id.desc()))
            if order is None:
                raise HTTPException(status_code=404, detail=f"{named[0].name} has no unpaid orders")
        elif named:
            raise HTTPException(status_code=422, detail="More than one customer matches. Say the full name or the order number.")
        else:
            raise HTTPException(status_code=404, detail="I could not find that customer. Say the name as saved, or the order number.")
        if order is None:
            raise HTTPException(status_code=404, detail="I could not find that order")
        if order.payment_status == "paid":
            raise HTTPException(status_code=409, detail=f"{order.code} is already paid")
        who = db.get(Customer, order.customer_id)
        return _proposal(db, business_id, actor_id, session_id, "request_payment", {"order_id": order.id},
                         f"Send {who.name if who else 'the customer'} the payment QR for {order.code}, {order.total_paise / 100:.0f} rupees")

    # 1. Reply: the message itself is taken from the original words, never rewritten.
    # Speech to text often mishears "saying" ("Singh", "sing") or adds a stray "to"; the connector word is optional.
    match = re.search(r"\b(?:reply|send reply|respond)\s+(?:to\s+)?(?:chat\s+)?(?:to\s+)?(?:number\s+)?(\w+)\b[\s,.:;-]*(.+)$", raw, re.I)
    number = voice_text.word_to_int(match.group(1)) if match else None
    if match and number is not None:
        reply = re.sub(r"^(?:saying|say|sing|singh|with|that|message)\b[\s,.:;-]*", "", match.group(2).strip(), flags=re.I).strip(" \"'")
        conv = db.get(Conversation, number)
        if conv is None or conv.business_id != business_id or not reply:
            raise HTTPException(status_code=404, detail="Chat or reply not found")
        return _proposal(db, business_id, actor_id, session_id, "send_reply", {"conversation_id": conv.id, "text": reply[:1000]},
                         f"Reply to {conv.display_name}: {reply[:180]}")

    # An order number without an action is a search request; answer it instead of returning generic help.
    order_lookup = re.search(r"\b(?:ord[- ]?\d+|order\s+\d{3,})\b", low)
    if order_lookup and not re.search(r"\b(confirm|pack|mark|ship|deliver|cancel)\b", low):
        code = re.sub(r"\s+", "", order_lookup.group(0)).upper()
        if code.startswith("ORD"):
            code = "ORD-" + re.sub(r"^ORD-?", "", code)
        elif code.startswith("ORDER"):
            code = "ORD-" + re.sub(r"^ORDER", "", code)
        order = db.scalar(select(Order).where(Order.business_id == business_id, Order.code == code))
        if order is None:
            raise HTTPException(status_code=404, detail=f"I could not find {code}")
        customer = db.get(Customer, order.customer_id)
        summary = f"{order.code} for {customer.name if customer else 'customer'} is {order.status}; total {order.total_paise / 100:.2f} rupees, payment {order.payment_status}."
        return _read(db, business_id, actor_id, "order lookup", summary,
                     order={"id": order.id, "code": order.code, "status": order.status,
                            "customer_name": customer.name if customer else "Customer", "total_paise": order.total_paise,
                            "payment_status": order.payment_status},
                     items=[{"id": order.id, "code": order.code,
                             "customer_name": customer.name if customer else "Customer",
                             "status": order.status, "total_paise": order.total_paise,
                             "payment_status": order.payment_status}])

    # Order pipeline actions are proposals too; cancellation can never happen from an unreviewed transcript.
    status_command = re.search(
        r"\b(confirm|pack|mark|ship|deliver|cancel)\s+(?:the\s+)?order\s+(ord[- ]?\d+)\b"
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
    count_match = re.search(
        r"\b(?:count|counted|stock count|ginti)\s+(\d{1,6})\b|"
        r"\b(?:set|adjust)\s+(?:the\s+)?stock\s+(?:of\s+)?(?:\w+\s+){0,4}?(?:to|at)\s+(\d{1,6})\b", low)
    if count_match or ("ginti" in low and re.search(r"\d{1,6}", low)):
        qty = int(next(g for g in count_match.groups() if g)) if count_match else int(re.search(r"\d{1,6}", low).group(0))
        if len(mentioned) != 1 or mentioned[0].kind != "ready_stock":
            raise HTTPException(status_code=422, detail="Say ‘count [quantity] for [ready stock item]’ so I can identify one item")
        item = mentioned[0]
        return _proposal(db, business_id, actor_id, session_id, "stock_count", {"item_id": item.id, "quantity": qty},
                         f"Set {item.name} stock to {qty} (currently {item.quantity or 0})")

    # 2. Restock: a verb, a number and an item.
    qty_match = re.search(r"\b(\d{1,6})\b", low) or re.search(r"\b(do)\b(?=.*\b(?:add|jodo|jod|restock)\b)", low)
    if re.search(r"\b(restock|add stock|add|received|stock up|increase|raise|jodo|jod do|badhao)\b", low) and qty_match:
        qty = 2 if qty_match.group(1) == "do" else int(qty_match.group(1))
        if len(mentioned) != 1 or mentioned[0].kind != "ready_stock" or qty < 1:
            raise HTTPException(status_code=422, detail="I could not match that ready stock item and quantity")
        item = mentioned[0]
        return _proposal(db, business_id, actor_id, session_id, "restock", {"item_id": item.id, "quantity": qty},
                         f"Add {qty} to {item.name} (current stock {item.quantity or 0})")

    # 3. Voice order: "rahul bought 80 roses, total 1600"
    if re.search(r"\b(?:bought|ordered|purchased|khareede|ne liye|place (?:an? )?order|create (?:an? )?order|make (?:an? )?order|new order|order banao)\b", low):
        from ..ai.extractor import parse_voice_order
        parsed = parse_voice_order(text)
        customer = parsed["customer"]
        lines = []
        names = []
        for item in mentioned:
            quantity = _item_quantity(low, item)
            lines.append({"catalog_item_id": item.id, "quantity": quantity})
            names.append(f"{quantity} × {item.name}")
        for draft in ([] if mentioned else parsed["items"]):
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
        if not mentioned and lines and lines[0]["catalog_item_id"] and len(items) == 1:
            lines[0]["quantity"] = _item_quantity(low, items[0])
        return _proposal(db, business_id, actor_id, session_id, "create_order", payload,
                         f"Create order for {customer['name']}: {', '.join(names)}. Prices will come from your catalog.")

    # 4. Low stock
    if re.search(r"\blow\b.*\bstock\b|\bstock\b.*\blow\b|running low|\bkam stock\b|\bstock kam\b|\bkya kam\b", low):
        low_items = [i for i in items if i.kind == "ready_stock" and (i.quantity or 0) <= inventory_service.LOW_STOCK_AT]
        low_items.sort(key=lambda i: (i.quantity or 0, i.name))
        summary = "No items are low on stock." if not low_items else "Low stock: " + "; ".join(
            f"{i.name}, {i.quantity or 0} left" for i in low_items)
        return _read(db, business_id, actor_id, "low stock", summary,
                     items=[{"id": i.id, "name": i.name, "quantity": i.quantity or 0, "kind": i.kind} for i in low_items])

    # 5. Today's DMs
    if re.search(r"\b(dms?|messages?|inbox|chats?)\b", low) and re.search(r"\b(read|show|tell|check|any|new|today|todays|aaj)\b", low):
        rows = db.scalars(select(Conversation).where(Conversation.business_id == business_id,
            Conversation.last_message_at >= utcnow().replace(hour=0, minute=0, second=0, microsecond=0))
            .order_by(Conversation.last_message_at.desc()).limit(20)).all()
        summary = "No DMs today." if not rows else f"You have {len(rows)} chats updated today. " + "; ".join(
            f"{c.display_name}: {c.last_preview}" for c in rows[:5])
        return _read(db, business_id, actor_id, "today's DMs", summary,
                     items=[{"name": c.display_name, "preview": c.last_preview, "status": c.status} for c in rows[:8]])

    if re.search(r"\b(orders?|sales)\b", low) and re.search(r"\b(read|show|list|check|today|todays|recent|how many|kitne|kitna)\b", low):
        q = select(Order, Customer).join(Customer, Customer.id == Order.customer_id).where(Order.business_id == business_id).order_by(Order.id.desc()).limit(12)
        rows = db.execute(q).all()
        total = sum(o.total_paise for o, _ in rows if o.status != "cancelled")
        summary = "No orders yet." if not rows else f"{len(rows)} recent orders worth {total / 100:.2f} rupees. " + "; ".join(
            f"{o.code}, {c.name}, {o.status}, {o.total_paise / 100:.2f} rupees" for o, c in rows[:6])
        return _read(db, business_id, actor_id, "recent orders", summary,
                     items=[{"id": o.id, "code": o.code, "customer_name": c.name, "status": o.status,
                             "total_paise": o.total_paise, "payment_status": o.payment_status} for o, c in rows])

    # 6. "How many roses are left?" and the Hinglish forms
    asks_stock = re.search(r"\b(how many|how much|kitne|kitna|kitni|stock|left|bache|bacha|bachi|remaining|available|in stock|do i have|hai kya|inventory)\b", low)
    if asks_stock:
        if mentioned:
            return _read(db, business_id, actor_id, "stock question", " ".join(_stock_line(db, i) for i in mentioned[:5]),
                         items=[{"id": i.id, "name": i.name, "kind": i.kind, "quantity": i.quantity,
                                 "capacity": i.capacity, "available": order_service.availability(db, i)} for i in mentioned[:5]])
        if re.search(r"\b(all|everything|overall|inventory|stock|my stock|list|show|read)\b", low):
            summary = "No catalog items yet." if not items else "Stock: " + "; ".join(_stock_line(db, i) for i in items[:12])
            return _read(db, business_id, actor_id, "stock overview", summary,
                         items=[{"id": i.id, "name": i.name, "kind": i.kind, "quantity": i.quantity,
                                 "capacity": i.capacity, "available": order_service.availability(db, i)} for i in items[:12]])
        names = ", ".join(i.name for i in items[:8]) or "none yet"
        _log(db, business_id, actor_id, "unmatched", raw[:200])
        db.commit()
        return {"type": "needs_clarification", "text": f"Which item do you mean? Your items: {names}."}

    _log(db, business_id, actor_id, "unmatched", raw[:200])
    db.commit()
    return {"type": "needs_clarification", "text": "Sorry, I did not get that. Try: open orders, how many roses are left, or say what can I say."}


YES_WORDS = {"yes", "yeah", "yep", "yas", "confirm", "confirmed", "ok", "okay", "sure", "send", "proceed",
             "haan", "han", "ha", "haa", "kar", "karo", "bhej", "theek", "sahi", "done"}
NO_WORDS = {"no", "nope", "nahi", "nahin", "na", "stop", "dont", "don", "wrong", "galat", "mat"}


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
        words = set(re.findall(r"[a-z]+", voice_text.to_latin(voice_phrase).casefold()))
        yes = words & YES_WORDS
        if words & NO_WORDS and not (row.action == "order_status" and "cancel" in words and yes):
            row.consumed_at = utcnow()
            _log(db, business_id, actor_id, "drop", row.summary)
            db.commit()
            return {"type": "dropped", "text": "Okay, I dropped that. Nothing was changed."}
        if not yes:
            raise HTTPException(status_code=403, detail="I did not hear a clear yes, so nothing was changed")
        # Cancelling an order is the one action that needs the extra word, so a stray "yes" cannot trigger it.
        if row.action == "order_status" and row.payload.get("status") == "cancelled" and "cancel" not in words:
            raise HTTPException(status_code=403, detail="To cancel an order, say yes cancel")
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
    elif row.action == "request_payment":
        order = db.get(Order, row.payload["order_id"])
        if order is None or order.business_id != business_id:
            raise HTTPException(status_code=404, detail="Order not found")
        sent = payment_service.notify_customer(db, order)
        who = db.get(Customer, order.customer_id)
        link = sent.get("payment_link")
        if link and sent["status"] in {"ready_to_share", "failed"}:
            # Not delivered over Instagram or WhatsApp: put the QR link in the customer's chat so it is ready to send.
            conv = db.scalar(select(Conversation).where(Conversation.business_id == business_id,
                                                        Conversation.customer_id == order.customer_id)
                             .order_by(Conversation.last_message_at.desc()).limit(1))
            if conv is not None:
                conversation_service.add_message(db, conv, "out", "owner",
                    f"Payment for order {order.code}, ₹{order.total_paise / 100:.2f}. Scan the QR or open: {link}")
        result = {"type": "completed", "order_id": order.id, "payment_link": link,
                  "text": f"Payment request for {order.code}" + (f" to {who.name}" if who else "") + ". " + sent["message"]}
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