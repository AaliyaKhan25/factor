"""UPI QR payment links and pending payment list."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, require_permission
from ..models.order import Order
from ..services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/pending")
def pending(ctx: Ctx = Depends(require_permission("view_orders")), db: Session = Depends(get_db)):
    return payment_service.pending_orders(db, ctx.business_id)


def _public_order(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Payment page not found")
    return order


@router.get("/public/{order_id}")
def public_payment(order_id: int, signature: str = Query(min_length=64, max_length=64), db: Session = Depends(get_db)):
    return payment_service.public_details(db, _public_order(db, order_id), signature)


@router.get("/public/{order_id}/qr")
def public_qr(order_id: int, signature: str = Query(min_length=64, max_length=64), db: Session = Depends(get_db)):
    return Response(content=payment_service.qr_svg(db, _public_order(db, order_id), signature), media_type="image/svg+xml",
                    headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/public/{order_id}/qr.png")
def public_qr_png(order_id: int, signature: str = Query(min_length=64, max_length=64), db: Session = Depends(get_db)):
    return Response(content=payment_service.qr_png(db, _public_order(db, order_id), signature), media_type="image/png",
                    headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})
