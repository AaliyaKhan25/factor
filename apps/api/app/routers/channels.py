"""Connect Instagram or WhatsApp. Each connection gets a webhook URL for Meta to call.

Receiving real messages needs a Meta app with the right permissions and app review, and a public HTTPS URL.
"""
import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import Ctx, get_admin_ctx
from ..models.channel_connection import ChannelConnection
from ..schemas.inbox import ChannelIn
from ..services import activity_service, conversation_service

router = APIRouter(tags=["channels"])


def _view(c: ChannelConnection) -> dict:
    return {"id": c.id, "channel": c.channel, "label": c.label, "verify_token": c.verify_token, "webhook_path": f"/webhooks/meta/{c.verify_token}"}


@router.get("/channels")
def list_channels(ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    rows = db.scalars(select(ChannelConnection).where(ChannelConnection.business_id == ctx.business_id).order_by(ChannelConnection.id)).all()
    return [_view(c) for c in rows]


@router.post("/channels", status_code=201)
def connect_channel(body: ChannelIn, ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    conn = ChannelConnection(business_id=ctx.business_id, channel=body.channel, label=body.label, verify_token=secrets.token_urlsafe(24))
    db.add(conn)
    db.flush()
    activity_service.log(db, business_id=ctx.business_id, actor_user_id=ctx.user.id, action="channel.connect", entity="channel", entity_id=conn.id, detail=body.channel)
    db.commit()
    return _view(conn)


@router.delete("/channels/{channel_id}")
def disconnect_channel(channel_id: int, ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    conn = db.get(ChannelConnection, channel_id)
    if conn is None or conn.business_id != ctx.business_id:
        raise HTTPException(status_code=404, detail="Channel not found")
    db.delete(conn)
    db.commit()
    return {"status": "removed"}


@router.get("/webhooks/meta/{token}", response_class=PlainTextResponse)
def verify_webhook(
    token: str,
    mode: str = Query(alias="hub.mode", default=""),
    verify: str = Query(alias="hub.verify_token", default=""),
    challenge: str = Query(alias="hub.challenge", default=""),
    db: Session = Depends(get_db),
):
    conn = db.scalar(select(ChannelConnection).where(ChannelConnection.verify_token == token))
    if conn is None or mode != "subscribe" or not hmac.compare_digest(verify, token):
        raise HTTPException(status_code=403, detail="Verification failed")
    return challenge


def _messages(payload: dict, channel: str):
    """Yield (handle, name, text) from an Instagram or WhatsApp Cloud API payload."""
    for entry in payload.get("entry", []):
        for ev in entry.get("messaging", []):                      # Instagram
            text = (ev.get("message") or {}).get("text")
            sender = (ev.get("sender") or {}).get("id")
            if text and sender and not (ev.get("message") or {}).get("is_echo"):
                yield str(sender), f"Instagram user {str(sender)[-4:]}", text
        for change in entry.get("changes", []):                    # WhatsApp
            value = change.get("value") or {}
            names = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts", [])}
            for m in value.get("messages", []):
                if m.get("type") == "text" and (m.get("text") or {}).get("body"):
                    frm = m.get("from", "")
                    yield frm, names.get(frm) or f"+{frm}", m["text"]["body"]


@router.post("/webhooks/meta/{token}")
async def receive_webhook(token: str, request: Request, db: Session = Depends(get_db)):
    conn = db.scalar(select(ChannelConnection).where(ChannelConnection.verify_token == token))
    if conn is None:
        raise HTTPException(status_code=404, detail="Unknown webhook")
    raw = await request.body()
    if settings.meta_app_secret:
        sig = request.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(settings.meta_app_secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=403, detail="Bad signature")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    n = 0
    for handle, name, text in _messages(payload, conn.channel):
        conversation_service.ingest(db, conn.business_id, conn.channel, handle, name, text)
        n += 1
    db.commit()
    return {"received": n}
