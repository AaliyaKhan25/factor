"""Customer book."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, require_permission
from ..models.customer import Customer
from ..models.order import Order

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("")
def list_customers(ctx: Ctx = Depends(require_permission("view_orders")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            Customer,
            func.count(Order.id),
            func.coalesce(func.sum(Order.total_paise), 0),
        )
        .outerjoin(Order, (Order.customer_id == Customer.id) & (Order.status != "cancelled"))
        .where(Customer.business_id == ctx.business_id)
        .group_by(Customer.id)
        .order_by(Customer.id.desc())
    ).all()
    return [
        {"id": c.id, "name": c.name, "phone": c.phone, "handle": c.handle, "orders": n, "spent_paise": int(total)}
        for c, n, total in rows
    ]
