"""The inbox agent. Rule-based on purpose.

It only does two things with the customer's text: spot what they are asking about, and decide whether the
owner must step in. Every price, quantity and availability figure comes from the catalog through
order_service, never from the text. Anything it is not sure about goes to the owner.
"""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.catalog_item import CatalogItem
from ..models.conversation import Conversation
from ..models.order import Order
from ..models.order_event import OrderEvent
from ..schemas.orders import CustomerIn, LineIn, OrderCreate
from . import order_service

ESCALATE: list[tuple[str, tuple[str, ...]]] = [
    ("Complaint or return", (
        "not delivered", "not received", "refund", "return", "damaged", "broken", "wrong item", "fake",
        "cheat", "complaint", "scam", "never came", "nahi mila", "nahi aaya", "not arrived")),
    ("Payment claim to verify", ("paid", "payment done", "payment kar", "sent the money", "screenshot", "utr", "transaction id")),
    ("Wants to bargain", (
        "discount", "bargain", "kam karo", "kam kar", "thoda kam", "cheaper", "less price", "best price",
        "last price", "reduce the price", "price kam")),
    ("Custom request", (
        "custom", "personali", "name on", "engrave", "my dog", "my cat", "special design", "own design",
        "make me a", "different color", "different colour", "my size")),
]
ORDER_INTENT = (
    "confirm", "book it", "book kar", "i'll take", "i will take", "want to order", "place order", "chahiye",
    "chaiye", "lena hai", "le lunga", "le lungi", "order kar", "bhej do", "i want",
)
TRACKING_INTENT = (
    "where is my order", "where's my order", "track my order", "track order", "order status",
    "kahan hai mera order", "mera order kahan", "order kahan hai", "mera parcel kahan", "kab ayega",
)
PRICE_INTENT = ("price", "how much", "kitne", "kitna", "rate", "cost", "available", "stock", "hai kya")
GREETINGS = ("hi", "hello", "hey", "hii", "namaste", "hlo")
STOP = {"the", "and", "for", "with", "set", "of", "a", "in"}


def rupees(paise: int) -> str:
    return f"Rs {paise // 100:,}" if paise % 100 == 0 else f"Rs {paise / 100:,.2f}"


def _words(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9']+", text.lower()):
        w = w[:-1] if len(w) > 3 and w.endswith("s") else w
        if len(w) >= 3 and w not in STOP:
            out.append(w)
    return out


def _match_item(text: str, items: list[CatalogItem]) -> tuple[CatalogItem | None, str | None, bool]:
    """Returns (item, matched word, ambiguous)."""
    tokens = set(_words(text))
    best, best_score, best_word, tie = None, 0, None, False
    for it in items:
        hits = [w for w in _words(it.name) if w in tokens]
        score = len(hits)
        if score > best_score:
            best, best_score, best_word, tie = it, score, hits[0], False
        elif score == best_score and score > 0:
            tie = True
    return (best if best_score else None), best_word, tie


def _quantity(text: str, word: str | None) -> int:
    t = text.lower()
    if word:
        m = re.search(rf"(\d{{1,2}})\s*(?:x\s*)?(?:[a-z]+\s+)?{re.escape(word)}", t) or re.search(
            rf"{re.escape(word)}\w*\s*(?:x|\*)\s*(\d{{1,2}})", t
        )
        if m:
            n = int(m.group(1))
            if 1 <= n <= 50:
                return n
    return 1


def _catalog_list(items: list[CatalogItem]) -> str:
    return "\n".join(f"- {i.name}: {rupees(i.price_paise)}" for i in items[:6])


class Decision:
    def __init__(self, reply: str, escalate: str | None = None, order_note: str | None = None):
        self.reply = reply
        self.escalate = escalate
        self.order_note = order_note


def decide(db: Session, conv: Conversation, text: str) -> Decision:
    low = text.lower()
    if any(phrase in low for phrase in TRACKING_INTENT):
        active_orders = db.scalars(
            select(Order).where(
                Order.business_id == conv.business_id,
                Order.customer_id == conv.customer_id,
                Order.status != "cancelled",
            ).order_by(Order.id.desc())
        ).all()
        if len(active_orders) != 1:
            return Decision("I couldn’t match exactly one active order, so I’ve asked the owner to help.", escalate="Order tracking needs an owner")
        order = active_orders[0]
        from ..models.courier import CourierShipment
        shipment = db.scalar(select(CourierShipment).where(
            CourierShipment.business_id == conv.business_id, CourierShipment.order_id == order.id
        ))
        if shipment:
            status = shipment.status.replace("_", " ")
            when = shipment.updated_at.strftime("%d %b at %I:%M %p UTC")
            reply = f"Your order {order.code} is {status}. The latest update was {when}."
            if shipment.tracking_url:
                reply += f" Track it here: {shipment.tracking_url}"
            return Decision(reply)
        event = db.scalar(select(OrderEvent).where(OrderEvent.order_id == order.id).order_by(OrderEvent.id.desc()).limit(1))
        when = event.created_at.strftime("%d %b at %I:%M %p UTC") if event else order.created_at.strftime("%d %b at %I:%M %p UTC")
        return Decision(f"Your order {order.code} is {order.status}. The latest update was {when}; tracking details aren’t available yet.")
    for reason, keys in ESCALATE:
        if any(k in low for k in keys):
            return Decision("Thanks for telling me. I have passed this to the owner, who will reply here soon.", escalate=reason)

    items = list(
        db.scalars(
            select(CatalogItem).where(CatalogItem.business_id == conv.business_id, CatalogItem.active.is_(True)).order_by(CatalogItem.id)
        ).all()
    )
    if not items:
        return Decision("Thanks for your message. The owner will get back to you soon.", escalate="No catalog items set up yet")

    item, word, tie = _match_item(text, items)
    first = low.split()[:1]
    greeting = bool(first) and first[0].strip("!.,") in GREETINGS
    price_q = any(k in low for k in PRICE_INTENT)

    if item is None or tie:
        if tie:
            return Decision("Which one do you mean? Here is what I have:\n" + _catalog_list(items))
        if greeting or price_q:
            return Decision("Hi! Here is what I have right now:\n" + _catalog_list(items) + "\nTell me what you like and I will check it for you.")
        return Decision("Thanks for your message. I have passed this to the owner, who will reply here soon.", escalate="Not sure what they need")

    qty = _quantity(text, word)
    free = order_service.availability(db, item)
    if free <= 0:
        return Decision(f"Sorry, {item.name} is not available right now. I can tell the owner you are interested.")
    if qty > free:
        return Decision(f"I only have {free} of {item.name} right now ({rupees(item.price_paise)} each). Would you like {free}?")

    if any(k in low for k in ORDER_INTENT):
        return Decision("", order_note=f"{qty}|{item.id}")

    how = f"ready in about {item.lead_time_days} days" if item.kind == "made_to_order" and item.lead_time_days else f"{free} available"
    total = f" For {qty} that is {rupees(item.price_paise * qty)}." if qty > 1 else ""
    return Decision(f"{item.name} is {rupees(item.price_paise)} each, {how}.{total} Reply 'confirm' and I will book it for you.")


def place_order(db: Session, conv: Conversation, customer_name: str, phone: str | None, handle: str | None, note: str):
    qty, item_id = (int(x) for x in note.split("|"))
    body = OrderCreate(
        customer=CustomerIn(name=customer_name, phone=phone, handle=handle),
        source=conv.channel,
        items=[LineIn(catalog_item_id=item_id, quantity=qty)],
        note="Booked by the inbox agent",
    )
    order = order_service.create_order(db, conv.business_id, None, body)
    return order
