"""Signed webhook endpoints for connected channels and optional courier adapters."""
import hashlib
import hmac
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.encryption import decrypt
from ..db import get_db
from ..models.courier import CourierConnection
from ..schemas.couriers import CourierWebhookIn
from ..services import courier_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/courier/{token}")
async def courier_webhook(
    token: str,
    request: Request,
    x_courier_signature: str = Header(default=""),
    x_courier_timestamp: str = Header(default=""),
    db: Session = Depends(get_db),
):
    connection = db.scalar(select(CourierConnection).where(
        CourierConnection.webhook_token_hash == hashlib.sha256(token.encode()).hexdigest()
    ))
    if connection is None:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    try:
        timestamp = int(x_courier_timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="A signed timestamp is required") from exc
    if abs(time.time() - timestamp) > 300:
        raise HTTPException(status_code=401, detail="Webhook timestamp is outside the 5 minute window")
    raw_body = await request.body()
    try:
        secret = decrypt(connection.webhook_secret_encrypted).encode()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Webhook secret cannot be decrypted") from exc
    expected = hmac.new(secret, str(timestamp).encode() + b"." + raw_body, hashlib.sha256).hexdigest()
    received = x_courier_signature.removeprefix("sha256=").strip().lower()
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = CourierWebhookIn.model_validate_json(raw_body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid courier event payload") from exc
    try:
        return courier_service.process_webhook(
            db, connection=connection, event_id=payload.event_id, awb=payload.awb,
            order_code=payload.order_code, status=payload.status, detail=payload.detail,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
