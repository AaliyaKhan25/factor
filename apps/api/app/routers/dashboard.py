"""Overview numbers."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, require_permission
from ..services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def overview(ctx: Ctx = Depends(require_permission("view_orders")), db: Session = Depends(get_db)):
    return dashboard_service.build(db, ctx.business_id)
