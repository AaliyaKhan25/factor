"""Manual and signed-webhook courier tracking; order events remain the customer evidence timeline."""
import hashlib
import json
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.encryption import decrypt, encrypt
from ..deps import Ctx
from ..integrations import courier as courier_adapter
from ..models.courier import CourierConnection, CourierShipment, CourierWebhookEvent
from ..models.order import Order
from ..models.order_event import OrderEvent
from ..services import activity_service, order_service
from ..utils.time import utcnow


def shipment_view(shipment: CourierShipment | None) -> dict | None:
    if not shipment:
        return None
    return {"id": shipment.id, "courier_name": shipment.courier_name, "awb": shipment.awb,
            "tracking_url": shipment.tracking_url or None, "status": shipment.status,
            "status_detail": shipment.status_detail, "updated_at": shipment.updated_at,
            "courier_connection_id": shipment.courier_connection_id}


def scoped_order(db: Session, business_id: int, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.business_id != business_id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def get_shipment(db: Session, business_id: int, order_id: int) -> CourierShipment | None:
    return db.scalar(select(CourierShipment).where(CourierShipment.business_id == business_id, CourierShipment.order_id == order_id))


def save_shipment(db: Session, *, order: Order, name: str, awb: str, url: str, actor_id: int,
                  connection: CourierConnection | None = None) -> CourierShipment:
    shipment = get_shipment(db, order.business_id, order.id)
    if shipment is None:
        shipment = CourierShipment(business_id=order.business_id, order_id=order.id, courier_name=name, awb=awb)
        db.add(shipment)
        db.flush()
        kind = "courier_added"
    else:
        kind = "courier_updated"
        shipment.courier_name = name
        shipment.awb = awb
    shipment.tracking_url = url
    shipment.courier_connection_id = connection.id if connection else None
    shipment.status = shipment.status or "label_created"
    shipment.status_detail = "Tracking details added" if kind == "courier_added" else "Tracking details updated"
    shipment.updated_at = utcnow()
    db.add(OrderEvent(business_id=order.business_id, order_id=order.id, kind=kind,
                      detail=f"{name} · AWB {awb}", actor_user_id=actor_id))
    return shipment


def set_status(db: Session, *, shipment: CourierShipment, status: str, detail: str = "", actor_id: int | None = None) -> None:
    normalized = courier_adapter.normalize_status(status)
    order = db.get(Order, shipment.order_id)
    if order is None or order.business_id != shipment.business_id:
        raise HTTPException(status_code=404, detail="Order not found")
    if shipment.status == normalized and shipment.status_detail == detail:
        return
    shipment.status = normalized
    shipment.status_detail = detail.strip()[:300]
    shipment.updated_at = utcnow()
    event_detail = f"{shipment.courier_name} · {normalized.replace('_', ' ')}"
    if detail.strip():
        event_detail += f" · {detail.strip()}"
    db.add(OrderEvent(business_id=order.business_id, order_id=order.id, kind="courier_update",
                      detail=event_detail[:500], actor_user_id=actor_id))
    if normalized == "delivered" and order.status == "shipped":
        order_service.change_status(db, order, "delivered", actor_id)
    activity_service.log(db, business_id=order.business_id, actor_user_id=actor_id,
                         action="courier.status", entity="order", entity_id=order.id, detail=normalized)


def create_connection(db: Session, *, business_id: int, name: str, provider: str,
                      credentials: dict[str, str]) -> tuple[CourierConnection, str, str]:
    token = secrets.token_urlsafe(32)
    secret = secrets.token_urlsafe(40)
    try:
        encrypted_credentials = encrypt(json.dumps(credentials, separators=(",", ":"))) if credentials else ""
        encrypted_secret = encrypt(secret)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    connection = CourierConnection(
        business_id=business_id,
        name=name.strip(),
        provider=provider.strip().lower(),
        credentials_encrypted=encrypted_credentials,
        webhook_token_hash=hashlib.sha256(token.encode()).hexdigest(),
        webhook_secret_encrypted=encrypted_secret,
    )
    db.add(connection)
    db.flush()
    return connection, token, secret


def connection_view(connection: CourierConnection) -> dict:
    return {"id": connection.id, "name": connection.name, "provider": connection.provider,
            "credentials_configured": bool(connection.credentials_encrypted), "webhook_enabled": True,
            "created_at": connection.created_at}


def process_webhook(db: Session, *, connection: CourierConnection, event_id: str, awb: str,
                    order_code: str, status: str, detail: str) -> dict:
    duplicate = db.scalar(select(CourierWebhookEvent.id).where(
        CourierWebhookEvent.connection_id == connection.id, CourierWebhookEvent.event_id == event_id
    ))
    if duplicate:
        return {"ok": True, "duplicate": True}
    shipment = None
    order = None
    if awb.strip():
        shipment = db.scalar(select(CourierShipment).where(
            CourierShipment.business_id == connection.business_id, CourierShipment.awb == awb.strip()
        ))
        if shipment:
            order = db.get(Order, shipment.order_id)
    if order is None and order_code.strip():
        order = db.scalar(select(Order).where(
            Order.business_id == connection.business_id, Order.code == order_code.strip()
        ))
        if order:
            shipment = get_shipment(db, connection.business_id, order.id)
    if order is None:
        raise HTTPException(status_code=404, detail="No order matches this AWB or order code")
    if shipment is None:
        shipment = save_shipment(db, order=order, name=connection.name, awb=awb or order.code,
                                 url="", actor_id=None, connection=connection)
    elif shipment.courier_connection_id not in (None, connection.id):
        raise HTTPException(status_code=409, detail="Tracking is linked to a different courier connection")
    shipment.courier_connection_id = connection.id
    set_status(db, shipment=shipment, status=status, detail=detail, actor_id=None)
    db.add(CourierWebhookEvent(connection_id=connection.id, event_id=event_id))
    db.commit()
    return {"ok": True, "duplicate": False, "order_code": order.code, "status": shipment.status}


def poll_order(db: Session, *, order: Order) -> dict:
    shipment = get_shipment(db, order.business_id, order.id)
    if shipment is None:
        raise HTTPException(status_code=404, detail="Add courier and AWB details first")
    connection = db.get(CourierConnection, shipment.courier_connection_id) if shipment.courier_connection_id else None
    if connection is None:
        raise HTTPException(status_code=409, detail="This shipment is in manual mode; update its status by hand")
    try:
        credentials = json.loads(decrypt(connection.credentials_encrypted)) if connection.credentials_encrypted else {}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Courier credentials could not be decrypted") from exc
    next_status = courier_adapter.adapter_for(connection.provider).poll(credentials, shipment.awb)
    if next_status:
        set_status(db, shipment=shipment, status=next_status, actor_id=None)
        db.commit()
    return shipment_view(shipment) or {}
