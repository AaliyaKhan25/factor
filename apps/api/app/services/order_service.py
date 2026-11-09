"""Order rules: availability, price, stock and the status pipeline.

Code decides these, never the client and never the AI. Quantities and prices come from the catalog.
"""
import re
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.catalog_item import CatalogItem
from ..models.customer import Customer
from ..models.order import Order
from ..models.order_event import OrderEvent
from ..models.order_item import OrderItem
from ..schemas.orders import OrderCreate
from . import inventory_service

OPEN_STATUSES = ("new", "confirmed", "packed", "shipped")

# current status -> statuses it may move to
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "new": ("confirmed", "cancelled"),
    "confirmed": ("packed", "cancelled"),
    "packed": ("shipped", "cancelled"),
    "shipped": ("delivered",),
    "delivered": (),
    "cancelled": (),
}


def add_event(db: Session, order: Order, kind: str, actor_id: int | None, detail: str = "") -> None:
    db.add(
        OrderEvent(
            business_id=order.business_id, order_id=order.id, kind=kind, detail=detail[:500], actor_user_id=actor_id
        )
    )


def open_quantity(db: Session, business_id: int, catalog_item_id: int) -> int:
    """Units of this item sitting in orders that are not yet delivered or cancelled."""
    total = db.scalar(
        select(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.business_id == business_id,
            OrderItem.catalog_item_id == catalog_item_id,
            Order.status.in_(OPEN_STATUSES),
        )
    )
    return int(total or 0)


def availability(db: Session, item: CatalogItem) -> int:
    """How many more units can be taken right now."""
    if item.kind == "ready_stock":
        return item.quantity or 0
    return max((item.capacity or 0) - open_quantity(db, item.business_id, item.id), 0)


def find_or_create_customer(db: Session, business_id: int, data) -> Customer:
    existing = None
    if data.phone:
        existing = db.scalar(select(Customer).where(Customer.business_id == business_id, Customer.phone == data.phone))
    elif data.handle:
        existing = db.scalar(select(Customer).where(Customer.business_id == business_id, Customer.handle == data.handle))
    if existing:
        return existing
    c = Customer(business_id=business_id, name=data.name.strip(), phone=data.phone, handle=data.handle)
    db.add(c)
    db.flush()
    return c


def _next_code(db: Session, business_id: int) -> str:
    codes = db.scalars(select(Order.code).where(Order.business_id == business_id)).all()
    nums = [int(m.group(1)) for c in codes if (m := re.fullmatch(r"ORD-(\d+)", c))]
    return f"ORD-{(max(nums) if nums else 1000) + 1}"


def create_order(db: Session, business_id: int, actor_id: int | None, body: OrderCreate) -> Order:
    # merge repeated lines for the same item so the availability check sees the full amount
    wanted: dict[int, int] = {}
    for line in body.items:
        wanted[line.catalog_item_id] = wanted.get(line.catalog_item_id, 0) + line.quantity

    items: list[tuple[CatalogItem, int]] = []
    for item_id, qty in wanted.items():
        item = db.get(CatalogItem, item_id)
        if item is None or item.business_id != business_id or not item.active:
            raise HTTPException(status_code=404, detail="Item not found")
        free = availability(db, item)
        if qty > free:
            raise HTTPException(
                status_code=409,
                detail=f"Only {free} of {item.name} available" if free else f"{item.name} is not available",
            )
        items.append((item, qty))

    customer = find_or_create_customer(db, business_id, body.customer)
    order = Order(
        business_id=business_id,
        code=_next_code(db, business_id),
        customer_id=customer.id,
        source=body.source,
        note=body.note,
        created_by=actor_id,
        total_paise=sum(i.price_paise * q for i, q in items),
    )
    db.add(order)
    db.flush()
    for item, qty in items:
        db.add(
            OrderItem(
                order_id=order.id,
                catalog_item_id=item.id,
                name=item.name,
                quantity=qty,
                unit_price_paise=item.price_paise,
            )
        )
        if item.kind == "ready_stock":
            before = item.quantity or 0
            inventory_service.ensure_opening(db, item, actor_id, balance=before)
            item.quantity = before - qty
            inventory_service.record(
                db, item, kind="sale", delta=-qty, balance=item.quantity, actor_id=actor_id,
                note=f"Order {order.code}",
            )
    add_event(db, order, "created", actor_id, f"source={body.source}")
    return order


def change_status(db: Session, order: Order, new_status: str, actor_id: int | None) -> None:
    if new_status not in TRANSITIONS[order.status]:
        raise HTTPException(status_code=409, detail=f"Cannot move an order from {order.status} to {new_status}")
    if new_status == "cancelled":
        # give ready stock back
        for line in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all():
            item = db.get(CatalogItem, line.catalog_item_id)
            if item is not None and item.kind == "ready_stock":
                inventory_service.ensure_opening(db, item, actor_id)
                item.quantity = (item.quantity or 0) + line.quantity
                inventory_service.record(
                    db, item, kind="cancellation", delta=line.quantity, balance=item.quantity,
                    actor_id=actor_id, note=f"Order {order.code} cancelled",
                )
    order.status = new_status
    add_event(db, order, new_status, actor_id)
