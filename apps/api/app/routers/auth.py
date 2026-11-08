"""Signup, login and the current user."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import secrets

from ..config import settings
from ..core import google as google_auth
from ..core.security import create_access_token, hash_password, verify_password
from ..db import get_db
from ..deps import get_current_user
from ..models.membership import Membership
from ..models.user import User
from ..schemas.auth import LoginRequest, SignupRequest
from ..schemas.inbox import GoogleIn
from ..services import activity_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", status_code=201)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    """Creates a plain account. No role, no business, no access until a business is created or joined."""
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    activity_service.log(
        db, business_id=None, actor_user_id=user.id, action="user.signup", entity="user", entity_id=user.id
    )
    db.commit()
    return {"id": user.id, "email": user.email, "name": user.name}


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Membership).where(Membership.user_id == user.id).order_by(Membership.id)).all()
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "memberships": [
            {"business_id": m.business_id, "role": m.role, "status": m.status} for m in rows
        ],
    }


@router.get("/config")
def public_config():
    """What the sign-in page needs to know. The Google client id is public by design."""
    return {"google_client_id": settings.google_client_id or None}


@router.post("/google")
def google_login(body: GoogleIn, db: Session = Depends(get_db)):
    """Sign in with a Google ID token. Creates a plain account the first time, never with any role."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not set up on this server")
    try:
        claims = google_auth.verify_google_token(body.credential)
    except Exception:
        raise HTTPException(status_code=401, detail="Google sign-in failed")
    email = str(claims.get("email", "")).lower()
    if not email or not claims.get("email_verified"):
        raise HTTPException(status_code=401, detail="Your Google email is not verified")
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, name=(claims.get("name") or email.split("@")[0])[:120], password_hash=hash_password(secrets.token_urlsafe(32)))
        db.add(user)
        db.flush()
        activity_service.log(db, business_id=None, actor_user_id=user.id, action="user.signup_google", entity="user", entity_id=user.id)
        db.commit()
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}
