"""Orders: create, list, detail with evidence timeline, status changes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, require_permission
from ..models.customer import Customer
from ..models.order import Order
from ..models.order_event import OrderEvent
from ..models.order_item import OrderItem
from ..models.conversation import Conversation
from ..schemas.orders import OrderCreate, StatusChange
from ..services import activity_service, order_service, payment_service, sheet_sync_service
from ..services.courier_service import get_shipment, shipment_view

router = APIRouter(prefix="/orders", tags=["orders"])


def _summary(o: Order, c: Customer) -> dict:
    return {
        "id": o.id,
        "code": o.code,
        "status": o.status,
        "payment_status": o.payment_status,
        "source": o.source,
        "total_paise": o.total_paise,
        "customer_name": c.name,
        "created_at": o.created_at,
    }


def _scoped(db: Session, ctx: Ctx, order_id: int) -> Order:
    o = db.get(Order, order_id)
    if o is None or o.business_id != ctx.business_id:
        raise HTTPException(status_code=404, detail="Order not found")
    return o


def _detail(db: Session, o: Order) -> dict:
    c = db.get(Customer, o.customer_id)
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == o.id).order_by(OrderItem.id)).all()
    events = db.scalars(select(OrderEvent).where(OrderEvent.order_id == o.id).order_by(OrderEvent.id)).all()
    conv = db.scalar(select(Conversation).where(
        Conversation.business_id == o.business_id, Conversation.customer_id == o.customer_id
    ).order_by(Conversation.last_message_at.desc()).limit(1))
    return {
        **_summary(o, c),
        "note": o.note,
        "customer": {"id": c.id, "name": c.name, "phone": c.phone, "handle": c.handle},
        "items": [
            {"name": i.name, "quantity": i.quantity, "unit_price_paise": i.unit_price_paise} for i in items
        ],
        "events": [{"kind": e.kind, "detail": e.detail, "created_at": e.created_at} for e in events],
        "tracking": shipment_view(get_shipment(db, o.business_id, o.id)),
        "payment": payment_service.payment_view(db, o),
        "linked_conversation": ({"id": conv.id, "channel": conv.channel, "display_name": conv.display_name} if conv else None),
        "next_statuses": list(order_service.TRANSITIONS[o.status]),
    }


@router.post("", status_code=201)
def create_order(body: OrderCreate, ctx: Ctx = Depends(require_permission("manage_orders")), db: Session = Depends(get_db)):
    order = order_service.create_order(db, ctx.business_id, ctx.user.id, body)
    activity_service.log(
        db, business_id=ctx.business_id, actor_user_id=ctx.user.id, action="order.create", entity="order", entity_id=order.id
    )
    db.commit()
    sheet_sync_service.enqueue_sync(db, ctx.business_id)
    return _detail(db, order)


@router.get("")
def list_orders(
    status: str | None = Query(default=None),
    ctx: Ctx = Depends(require_permission("view_orders")),
    db: Session = Depends(get_db),
):
    q = (
        select(Order, Customer)
        .join(Customer, Customer.id == Order.customer_id)
        .where(Order.business_id == ctx.business_id)
        .order_by(Order.id.desc())
    )
    if status:
        q = q.where(Order.status == status)
    rows = []
    for o, c in db.execute(q).all():
        conv = db.scalar(select(Conversation).where(
            Conversation.business_id == o.business_id, Conversation.customer_id == o.customer_id
        ).order_by(Conversation.last_message_at.desc()).limit(1))
        shipment = get_shipment(db, o.business_id, o.id)
        rows.append({**_summary(o, c), "linked_conversation_id": conv.id if conv else None,
                     "tracking": shipment_view(shipment)})
    return rows


@router.get("/{order_id}")
def get_order(order_id: int, ctx: Ctx = Depends(require_permission("view_orders")), db: Session = Depends(get_db)):
    return _detail(db, _scoped(db, ctx, order_id))


@router.post("/{order_id}/status")
def set_status(
    order_id: int, body: StatusChange, ctx: Ctx = Depends(require_permission("manage_orders")), db: Session = Depends(get_db)
):
    order = _scoped(db, ctx, order_id)
    order_service.change_status(db, order, body.status, ctx.user.id)
    activity_service.log(
        db,
        business_id=ctx.business_id,
        actor_user_id=ctx.user.id,
        action="order.status",
        entity="order",
        entity_id=order.id,
        detail=body.status,
    )
    db.commit()
    sheet_sync_service.enqueue_sync(db, ctx.business_id)
    detail = _detail(db, order)
    if body.status == "confirmed":
        detail["payment_delivery"] = payment_service.notify_customer(db, order)
    return detail
