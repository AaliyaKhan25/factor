"""Dependencies: current user, business scope, permission checks.

Every business-scoped endpoint gets a Ctx. Queries must filter by ctx.business_id so one
business can never see another's data.
"""
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .core.permissions import effective_permissions
from .core.security import decode_access_session, decode_access_token
from .db import get_db
from .models.membership import Membership
from .models.user import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)
) -> User:
    user_id = decode_access_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def active_membership(db: Session, user_id: int) -> Membership | None:
    return db.scalar(
        select(Membership).where(Membership.user_id == user_id, Membership.status == "active")
    )


@dataclass
class Ctx:
    user: User
    membership: Membership
    business_id: int
    permissions: frozenset[str]
    session_id: str


def get_ctx(user: User = Depends(get_current_user), db: Session = Depends(get_db), creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Ctx:
    """The signed-in user's active business. Pending, rejected and removed members get 403."""
    membership = active_membership(db, user.id)
    if membership is None:
        raise HTTPException(status_code=403, detail="No active business membership")
    return Ctx(
        user=user,
        membership=membership,
        business_id=membership.business_id,
        permissions=effective_permissions(membership.role, membership.extra_permissions),
        session_id=decode_access_session(creds.credentials) if creds else "",
    )


def get_admin_ctx(ctx: Ctx = Depends(get_ctx)) -> Ctx:
    """Only the owner can manage the team and assign roles."""
    if ctx.membership.role != "admin":
        raise HTTPException(status_code=403, detail="Only the owner can do this")
    return ctx


def require_permission(permission: str):
    def dependency(ctx: Ctx = Depends(get_ctx)) -> Ctx:
        if permission not in ctx.permissions:
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return ctx

    return dependency
