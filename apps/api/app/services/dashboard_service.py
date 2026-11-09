"""Numbers for the Overview screen. Everything is computed from real rows."""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.conversation import Conversation
from ..models.customer import Customer
from ..models.order import Order
from ..models.catalog_item import CatalogItem
from ..utils.time import utcnow


def build(db: Session, business_id: int) -> dict:
    now = utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_start = (month_start - timedelta(days=1)).replace(day=1)

    orders = db.scalars(select(Order).where(Order.business_id == business_id)).all()
    live = [o for o in orders if o.status != "cancelled"]

    this_month = sum(o.total_paise for o in live if o.created_at >= month_start)
    last_month = sum(o.total_paise for o in live if prev_start <= o.created_at < month_start)

    today = now.date()
    daily = {today - timedelta(days=i): 0 for i in range(27, -1, -1)}
    for o in live:
        d = o.created_at.date()
        if d in daily:
            daily[d] += o.total_paise

    unpaid = [o for o in live if o.payment_status == "unpaid"]
    new = [o for o in orders if o.status == "new"]
    confirmed = [o for o in orders if o.status == "confirmed"]
    packed = [o for o in orders if o.status == "packed"]
    shipped = [o for o in orders if o.status == "shipped"]

    convs = db.scalars(select(Conversation).where(Conversation.business_id == business_id)).all()
    needs = sorted((c for c in convs if c.status == "needs_owner"), key=lambda c: c.last_message_at)

    todo = []
    if needs:
        names = ", ".join(c.display_name for c in needs[:3])
        todo.append({"kind": "inbox", "title": f"Reply to {len(needs)} {'customer' if len(needs) == 1 else 'customers'}",
                     "detail": f"{names} {'is' if len(needs) == 1 else 'are'} waiting", "href": "/inbox"})
    if new:
        todo.append({"kind": "orders", "title": f"Confirm {len(new)} new {'order' if len(new) == 1 else 'orders'}",
                     "detail": ", ".join(o.code for o in new[:4]), "href": "/orders?status=new"})
    if unpaid:
        todo.append({"kind": "payments", "title": f"{len(unpaid)} {'order is' if len(unpaid) == 1 else 'orders are'} unpaid",
                     "detail": f"{sum(o.total_paise for o in unpaid) // 100:,} rupees to collect", "href": "/orders"})
    if packed:
        todo.append({"kind": "ship", "title": f"Ship {len(packed)} packed {'order' if len(packed) == 1 else 'orders'}",
                     "detail": ", ".join(o.code for o in packed[:4]), "href": "/orders?status=packed"})

    inventory = db.scalars(
        select(CatalogItem).where(CatalogItem.business_id == business_id, CatalogItem.active.is_(True), CatalogItem.kind == "ready_stock")
    ).all()
    out_of_stock = [i for i in inventory if (i.quantity or 0) == 0]
    low_stock = [i for i in inventory if 0 < (i.quantity or 0) <= 5]
    flagged = out_of_stock + low_stock
    if flagged:
        todo.append({
            "kind": "inventory",
            "title": f"{len(flagged)} item{'s' if len(flagged) != 1 else ''} running low",
            "detail": ", ".join(i.name for i in flagged[:3]),
            "href": "/inventory",
        })

    return {
        "sales_month_paise": this_month,
        "sales_prev_month_paise": last_month,
        "orders_to_fulfil": len(new) + len(confirmed) + len(packed),
        "ready_to_ship": len(packed),
        "in_progress": len(new) + len(confirmed) + len(shipped),
        "unpaid_count": len(unpaid),
        "unpaid_paise": sum(o.total_paise for o in unpaid),
        "messages_open": len(needs),
        "agent_handled": sum(1 for c in convs if c.status == "agent"),
        "daily": [{"date": d.isoformat(), "total_paise": v} for d, v in daily.items()],
        "todo": todo,
        "customers": db.query(Customer).filter(Customer.business_id == business_id).count(),
        "low_stock_count": len(low_stock),
        "out_of_stock_count": len(out_of_stock),
    }
