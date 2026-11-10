"""Connect an app-owned Google Sheet and run one-way snapshots."""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_admin_ctx
from ..models.sheet_connection import SheetConnection
from ..services import sheet_sync_service
from ..utils.time import utcnow

router = APIRouter(prefix="/sheets", tags=["google-sheets"])


class SheetConnectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spreadsheet_url: str = Field(min_length=20, max_length=500)


def _sheet_id(value: str) -> str:
    match = re.search(r"docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)", value.strip())
    if not match:
        raise HTTPException(status_code=422, detail="Paste a Google Sheets link")
    return match.group(1)


@router.get("")
def get_sheet_status(ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    return sheet_sync_service.status(db, ctx.business_id)


@router.post("")
@router.put("")
def connect_sheet(body: SheetConnectIn, ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    sheet_id = _sheet_id(body.spreadsheet_url)
    connection = db.scalar(select(SheetConnection).where(SheetConnection.business_id == ctx.business_id))
    if connection is None:
        connection = SheetConnection(business_id=ctx.business_id, spreadsheet_id=sheet_id, spreadsheet_url=body.spreadsheet_url.strip())
        db.add(connection)
    else:
        connection.spreadsheet_id = sheet_id
        connection.spreadsheet_url = body.spreadsheet_url.strip()
        connection.last_error = ""
        connection.updated_at = utcnow()
    db.commit()
    return sheet_sync_service.status(db, ctx.business_id)


@router.post("/sync-now")
def sync_now(ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    return sheet_sync_service.sync_business(db, ctx.business_id)


@router.delete("")
def disconnect_sheet(ctx: Ctx = Depends(get_admin_ctx), db: Session = Depends(get_db)):
    connection = db.scalar(select(SheetConnection).where(SheetConnection.business_id == ctx.business_id))
    if connection:
        db.delete(connection)
        db.commit()
    return {"connected": False, "last_synced_at": None, "last_error": ""}
