"""Courier setup (optional), manual AWB tracking, and adapter polling."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_admin_ctx, require_permission
from ..models.courier import CourierConnection
from ..schemas.couriers import CourierConnectionIn, ShipmentIn, ShipmentStatusIn
from ..services import activity_service, courier_service, sheet_sync_service

router = APIRouter(prefix="/couriers", tags=["couriers"])


@router.get("")
def connections(ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    return [courier_service.connection_view(c) for c in db.scalars(
        select(CourierConnection).where(CourierConnection.business_id == ctx.business_id).order_by(CourierConnection.id)
    ).all()]


@router.post("", status_code=201)
def add_connection(body: CourierConnectionIn, ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    connection, token, secret = courier_service.create_connection(
        db, business_id=ctx.business_id, name=body.name, provider=body.provider, credentials=body.credentials
    )
    activity_service.log(db, business_id=ctx.business_id, actor_user_id=ctx.user.id,
                         action="courier.connect", entity="courier", entity_id=connection.id)
    db.commit()
    return {**courier_service.connection_view(connection), "webhook_path": f"/webhooks/courier/{token}", "webhook_secret": secret}


@router.put("/orders/{order_id}/shipment")
def set_shipment(order_id: int, body: ShipmentIn, ctx: Ctx = Depends(require_permission("manage_orders")), db: Session = Depends(get_db)):
    order = courier_service.scoped_order(db, ctx.business_id, order_id)
    connection = None
    if body.courier_connection_id is not None:
        connection = db.get(CourierConnection, body.courier_connection_id)
        if connection is None or connection.business_id != ctx.business_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Courier connection not found")
    shipment = courier_service.save_shipment(
        db, order=order, name=body.courier_name, awb=body.awb.strip(),
        url=str(body.tracking_url) if body.tracking_url else "", actor_id=ctx.user.id, connection=connection,
    )
    db.commit()
    sheet_sync_service.enqueue_sync(db, ctx.business_id)
    return courier_service.shipment_view(shipment)


@router.post("/orders/{order_id}/status")
def update_shipment_status(order_id: int, body: ShipmentStatusIn, ctx: Ctx = Depends(require_permission("manage_orders")), db: Session = Depends(get_db)):
    order = courier_service.scoped_order(db, ctx.business_id, order_id)
    shipment = courier_service.get_shipment(db, ctx.business_id, order.id)
    if shipment is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Add courier and AWB details first")
    courier_service.set_status(db, shipment=shipment, status=body.status, detail=body.detail, actor_id=ctx.user.id)
    db.commit()
    sheet_sync_service.enqueue_sync(db, ctx.business_id)
    return courier_service.shipment_view(shipment)


@router.post("/orders/{order_id}/poll")
def poll_shipment(order_id: int, ctx: Ctx = Depends(require_permission("manage_orders")), db: Session = Depends(get_db)):
    order = courier_service.scoped_order(db, ctx.business_id, order_id)
    return courier_service.poll_order(db, order=order)
