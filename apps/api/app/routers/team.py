"""Join by code, pending requests, approve, set permissions, remove members."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.permissions import effective_permissions
from ..db import get_db
from ..deps import Ctx, active_membership, get_admin_ctx, get_current_user
from ..models.membership import Membership
from ..models.user import User
from ..schemas.team import JoinRequest, MemberAccess
from ..services import activity_service, invite_service
from ..utils.time import utcnow

router = APIRouter(prefix="/team", tags=["team"])

# Same message for unknown, revoked, expired and used-up codes, so nobody can probe which codes exist.
INVALID_CODE = "Invalid or expired business code"


def _view(m: Membership, u: User) -> dict:
    return {
        "id": m.id,
        "user_id": u.id,
        "name": u.name,
        "email": u.email,
        "role": m.role,
        "status": m.status,
        "permissions": sorted(effective_permissions(m.role, m.extra_permissions)),
    }


def _scoped_member(db: Session, ctx: Ctx, member_id: int) -> Membership:
    """A member of THIS business, or 404. Another business's members are invisible."""
    m = db.get(Membership, member_id)
    if m is None or m.business_id != ctx.business_id:
        raise HTTPException(status_code=404, detail="Member not found")
    return m


@router.post("/join", status_code=202)
def join(body: JoinRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Joining with a code only creates a pending request. It gives no access until the owner approves."""
    if active_membership(db, user.id):
        raise HTTPException(status_code=409, detail="You already belong to a business")
    code = invite_service.find_valid_code(db, body.code)
    if code is None:
        raise HTTPException(status_code=400, detail=INVALID_CODE)

    existing = db.scalar(
        select(Membership).where(Membership.business_id == code.business_id, Membership.user_id == user.id)
    )
    if existing is not None:
        if existing.status == "pending":
            raise HTTPException(status_code=409, detail="Your request is already waiting for approval")
        # rejected or removed people may ask again, always as a plain pending Employee
        existing.status = "pending"
        existing.role = "employee"
        existing.extra_permissions = []
        existing.decided_at = None
        existing.decided_by = None
        member = existing
    else:
        member = Membership(
            business_id=code.business_id, user_id=user.id, role="employee", status="pending", extra_permissions=[]
        )
        db.add(member)
        db.flush()

    code.use_count += 1
    activity_service.log(
        db,
        business_id=code.business_id,
        actor_user_id=user.id,
        action="team.join_requested",
        entity="membership",
        entity_id=member.id,
    )
    db.commit()
    return {"status": "pending", "message": "Request sent. The owner must approve it before you get access."}


@router.get("/members")
def list_members(ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.business_id == ctx.business_id)
        .order_by(Membership.id)
    ).all()
    return [_view(m, u) for m, u in rows]


@router.post("/members/{member_id}/approve")
def approve(member_id: int, body: MemberAccess, ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    m = _scoped_member(db, ctx, member_id)
    if m.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending requests can be approved")
    if active_membership(db, m.user_id):
        raise HTTPException(status_code=409, detail="This person already belongs to another business")
    m.role, m.extra_permissions = body.resolve()
    m.status = "active"
    m.decided_at = utcnow()
    m.decided_by = ctx.user.id
    activity_service.log(
        db,
        business_id=ctx.business_id,
        actor_user_id=ctx.user.id,
        action="team.approved",
        entity="membership",
        entity_id=m.id,
        detail=f"role={m.role}",
    )
    db.commit()
    return _view(m, db.get(User, m.user_id))


@router.patch("/members/{member_id}")
def update_access(member_id: int, body: MemberAccess, ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    m = _scoped_member(db, ctx, member_id)
    if m.status != "active" or m.role == "admin":
        raise HTTPException(status_code=409, detail="Only active team members can be changed")
    m.role, m.extra_permissions = body.resolve()
    activity_service.log(
        db,
        business_id=ctx.business_id,
        actor_user_id=ctx.user.id,
        action="team.access_changed",
        entity="membership",
        entity_id=m.id,
        detail=f"role={m.role}",
    )
    db.commit()
    return _view(m, db.get(User, m.user_id))


@router.post("/members/{member_id}/reject")
def reject(member_id: int, ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    m = _scoped_member(db, ctx, member_id)
    if m.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending requests can be rejected")
    m.status = "rejected"
    m.decided_at = utcnow()
    m.decided_by = ctx.user.id
    activity_service.log(
        db,
        business_id=ctx.business_id,
        actor_user_id=ctx.user.id,
        action="team.rejected",
        entity="membership",
        entity_id=m.id,
    )
    db.commit()
    return _view(m, db.get(User, m.user_id))


@router.delete("/members/{member_id}")
def remove(member_id: int, ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    m = _scoped_member(db, ctx, member_id)
    if m.role == "admin" or m.user_id == ctx.user.id:
        raise HTTPException(status_code=400, detail="The owner cannot be removed")
    if m.status not in ("active", "pending"):
        raise HTTPException(status_code=409, detail="This person is not on the team")
    m.status = "removed"
    m.decided_at = utcnow()
    m.decided_by = ctx.user.id
    activity_service.log(
        db,
        business_id=ctx.business_id,
        actor_user_id=ctx.user.id,
        action="team.removed",
        entity="membership",
        entity_id=m.id,
    )
    db.commit()
    return {"status": "removed"}
