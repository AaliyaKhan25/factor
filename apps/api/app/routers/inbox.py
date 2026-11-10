"""The inbox: conversations, split into 'needs you' and 'handled by the agent'."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, require_permission
from ..models.conversation import Conversation
from ..models.message import Message
from ..models.order import Order
from ..services.courier_service import get_shipment, shipment_view
from ..schemas.inbox import ConvStatusIn, ReplyIn, SimulateIn
from ..services import activity_service, conversation_service, payment_service

router = APIRouter(prefix="/inbox", tags=["inbox"])
Chat = Depends(require_permission("reply_to_chats"))


def _summary(c: Conversation) -> dict:
    return {
        "id": c.id,
        "channel": c.channel,
        "handle": c.handle,
        "display_name": c.display_name,
        "status": c.status,
        "reason": c.reason,
        "last_message_at": c.last_message_at,
        "last_preview": c.last_preview,
    }


def _scoped(db: Session, ctx: Ctx, conv_id: int) -> Conversation:
    c = db.get(Conversation, conv_id)
    if c is None or c.business_id != ctx.business_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return c


def _detail(db: Session, c: Conversation) -> dict:
    msgs = db.scalars(select(Message).where(Message.conversation_id == c.id).order_by(Message.id)).all()
    orders = []
    if c.customer_id:
        orders = db.scalars(select(Order).where(
            Order.business_id == c.business_id, Order.customer_id == c.customer_id
        ).order_by(Order.id.desc()).limit(5)).all()
    return {
        **_summary(c),
        "messages": [{"id": m.id, "direction": m.direction, "sender": m.sender, "text": m.text, "created_at": m.created_at} for m in msgs],
        "orders": [{"id": o.id, "code": o.code, "status": o.status, "total_paise": o.total_paise,
                    "created_at": o.created_at, "payment": payment_service.payment_view(db, o),
                    "tracking": shipment_view(get_shipment(db, c.business_id, o.id))}
                   for o in orders],
    }


@router.get("/counts")
def counts(ctx: Ctx = Chat, db: Session = Depends(get_db)):
    rows = db.execute(
        select(Conversation.status, func.count()).where(Conversation.business_id == ctx.business_id).group_by(Conversation.status)
    ).all()
    out = {"needs_owner": 0, "agent": 0, "resolved": 0}
    out.update({s: n for s, n in rows})
    return out


@router.get("/conversations")
def list_conversations(
    bucket: str = Query(default="all", pattern="^(all|needs_owner|agent|resolved)$"),
    ctx: Ctx = Chat,
    db: Session = Depends(get_db),
):
    q = select(Conversation).where(Conversation.business_id == ctx.business_id).order_by(Conversation.last_message_at.desc())
    if bucket != "all":
        q = q.where(Conversation.status == bucket)
    return [_summary(c) for c in db.scalars(q).all()]


@router.get("/conversations/{conv_id}")
def get_conversation(conv_id: int, ctx: Ctx = Chat, db: Session = Depends(get_db)):
    return _detail(db, _scoped(db, ctx, conv_id))


@router.post("/conversations/{conv_id}/reply")
def reply(conv_id: int, body: ReplyIn, ctx: Ctx = Chat, db: Session = Depends(get_db)):
    """Saved to the thread. Delivery to Instagram or WhatsApp needs the channel's send API, which is not connected yet."""
    c = _scoped(db, ctx, conv_id)
    conversation_service.add_message(db, c, "out", "owner", body.text.strip())
    activity_service.log(db, business_id=ctx.business_id, actor_user_id=ctx.user.id, action="inbox.reply", entity="conversation", entity_id=c.id)
    db.commit()
    return _detail(db, c)


@router.post("/conversations/{conv_id}/status")
def set_status(conv_id: int, body: ConvStatusIn, ctx: Ctx = Chat, db: Session = Depends(get_db)):
    c = _scoped(db, ctx, conv_id)
    c.status = body.status
    c.reason = "Taken over by you" if body.status == "needs_owner" else ""
    activity_service.log(
        db, business_id=ctx.business_id, actor_user_id=ctx.user.id, action="inbox.status", entity="conversation", entity_id=c.id, detail=body.status
    )
    db.commit()
    return _detail(db, c)


@router.post("/simulate", status_code=201)
def simulate(body: SimulateIn, ctx: Ctx = Chat, db: Session = Depends(get_db)):
    """Demo helper: acts as if this customer just sent a DM."""
    c = conversation_service.ingest(db, ctx.business_id, body.channel, body.handle.strip(), body.name.strip(), body.text)
    db.commit()
    return _detail(db, c)
