"""Business codes: generate, revoke and validate."""
import secrets
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..models.invite_code import InviteCode
from ..utils.time import utcnow

# No 0/O or 1/I so codes are easy to read out loud. 8 characters from 32 symbols.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_code() -> str:
    half = lambda: "".join(secrets.choice(_ALPHABET) for _ in range(4))  # noqa: E731
    return f"{half()}-{half()}"


def normalize(raw: str) -> str:
    compact = "".join(raw.split()).upper().replace("-", "")
    return f"{compact[:4]}-{compact[4:]}" if len(compact) == 8 else compact


def create_code(
    db: Session, business_id: int, *, expires_in_days: int | None = None, single_use: bool = False
) -> InviteCode:
    while True:
        code = generate_code()
        if db.scalar(select(InviteCode.id).where(InviteCode.code == code)) is None:
            break
    row = InviteCode(
        business_id=business_id,
        code=code,
        expires_at=utcnow() + timedelta(days=expires_in_days) if expires_in_days else None,
        single_use=single_use,
    )
    db.add(row)
    db.flush()
    return row


def revoke_active_codes(db: Session, business_id: int) -> None:
    db.execute(
        update(InviteCode)
        .where(InviteCode.business_id == business_id, InviteCode.revoked.is_(False))
        .values(revoked=True)
    )


def current_code(db: Session, business_id: int) -> InviteCode | None:
    return db.scalar(
        select(InviteCode)
        .where(InviteCode.business_id == business_id, InviteCode.revoked.is_(False))
        .order_by(InviteCode.id.desc())
    )


def find_valid_code(db: Session, raw: str) -> InviteCode | None:
    """Return the code row only if it can still be used. All failures look the same to callers."""
    row = db.scalar(select(InviteCode).where(InviteCode.code == normalize(raw)))
    if row is None or row.revoked:
        return None
    if row.expires_at is not None and row.expires_at <= utcnow():
        return None
    if row.single_use and row.use_count >= 1:
        return None
    return row
