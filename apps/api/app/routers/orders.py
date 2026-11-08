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
from ..schemas.orders import OrderCreate, StatusChange
from ..services import activity_service, order_service

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
    return {
        **_summary(o, c),
        "note": o.note,
        "customer": {"id": c.id, "name": c.name, "phone": c.phone, "handle": c.handle},
        "items": [
            {"name": i.name, "quantity": i.quantity, "unit_price_paise": i.unit_price_paise} for i in items
        ],
        "events": [{"kind": e.kind, "detail": e.detail, "created_at": e.created_at} for e in events],
        "next_statuses": list(order_service.TRANSITIONS[o.status]),
    }


@router.post("", status_code=201)
def create_order(body: OrderCreate, ctx: Ctx = Depends(require_permission("manage_orders")), db: Session = Depends(get_db)):
    order = order_service.create_order(db, ctx.business_id, ctx.user.id, body)
    activity_service.log(
        db, business_id=ctx.business_id, actor_user_id=ctx.user.id, action="order.create", entity="order", entity_id=order.id
    )
    db.commit()
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
    return [_summary(o, c) for o, c in db.execute(q).all()]


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
    return _detail(db, order)
