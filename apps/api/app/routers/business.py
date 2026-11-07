"""Create a business, read its details, regenerate the business code."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, active_membership, get_admin_ctx, get_ctx, get_current_user
from ..models.business import Business
from ..models.membership import Membership
from ..models.user import User
from ..schemas.business import BusinessCreate
from ..services import activity_service, invite_service
from ..utils.time import utcnow

router = APIRouter(prefix="/business", tags=["business"])


@router.post("", status_code=201)
def create_business(
    body: BusinessCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Starting your own business makes you its owner (admin). You can never become admin of an existing one."""
    if active_membership(db, user.id):
        raise HTTPException(status_code=409, detail="You already belong to a business")
    business = Business(
        name=body.name.strip(), upi_id=body.upi_id, language=body.language, template=body.template
    )
    db.add(business)
    db.flush()
    db.add(
        Membership(
            business_id=business.id,
            user_id=user.id,
            role="admin",
            status="active",
            extra_permissions=[],
            decided_at=utcnow(),
            decided_by=user.id,
        )
    )
    code = invite_service.create_code(db, business.id)
    activity_service.log(
        db,
        business_id=business.id,
        actor_user_id=user.id,
        action="business.create",
        entity="business",
        entity_id=business.id,
    )
    db.commit()
    return {"id": business.id, "name": business.name, "business_code": code.code}


@router.get("")
def get_business(ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    business = db.get(Business, ctx.business_id)
    data = {
        "id": business.id,
        "name": business.name,
        "upi_id": business.upi_id,
        "language": business.language,
        "template": business.template,
        "your_role": ctx.membership.role,
        "your_permissions": sorted(ctx.permissions),
    }
    if ctx.membership.role == "admin":
        code = invite_service.current_code(db, business.id)
        data["business_code"] = code.code if code else None
    return data


@router.post("/code/regenerate")
def regenerate_code(
    expires_in_days: int | None = Query(default=None, ge=1, le=365),
    single_use: bool = False,
    ctx: Ctx = Depends(get_admin_ctx),
    db: Session = Depends(get_db),
):
    """Revokes every active code and issues a new one."""
    invite_service.revoke_active_codes(db, ctx.business_id)
    code = invite_service.create_code(
        db, ctx.business_id, expires_in_days=expires_in_days, single_use=single_use
    )
    activity_service.log(
        db,
        business_id=ctx.business_id,
        actor_user_id=ctx.user.id,
        action="business.code_regenerated",
        entity="invite_code",
        entity_id=code.id,
    )
    db.commit()
    return {"business_code": code.code, "expires_at": code.expires_at, "single_use": code.single_use}
