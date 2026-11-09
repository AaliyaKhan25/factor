"""Live stock balances and append-only stock movement history."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, require_permission
from ..models.catalog_item import CatalogItem
from ..models.stock_log import StockLog
from ..schemas.inventory import StockAdjustment
from ..services import activity_service, inventory_service, sheet_sync_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _item(db: Session, ctx: Ctx, item_id: int) -> CatalogItem:
    item = db.get(CatalogItem, item_id)
    if item is None or item.business_id != ctx.business_id or not item.active:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


def _log(entry: StockLog) -> dict:
    return {"id": entry.id, "item_id": entry.catalog_item_id, "kind": entry.kind,
            "quantity_delta": entry.quantity_delta, "balance_after": entry.balance_after,
            "note": entry.note, "created_at": entry.created_at}


@router.get("")
def list_inventory(ctx: Ctx = Depends(require_permission("view_orders")), db: Session = Depends(get_db)):
    items = db.scalars(select(CatalogItem).where(CatalogItem.business_id == ctx.business_id, CatalogItem.active.is_(True)).order_by(CatalogItem.name)).all()
    rows = [inventory_service.view(db, item) for item in items]
    db.commit()  # backfill one opening balance for pre-ledger catalog items
    return {"items": rows, "low_stock_count": sum(1 for x in rows if x["low_stock"]), "out_of_stock_count": sum(1 for x in rows if x["out_of_stock"])}


@router.get("/{item_id}/history")
def item_history(item_id: int, ctx: Ctx = Depends(require_permission("view_orders")), db: Session = Depends(get_db)):
    item = _item(db, ctx, item_id)
    if item.kind != "ready_stock":
        return {"item": inventory_service.view(db, item), "history": []}
    rows = [_log(log) for log in inventory_service.history(db, item)]
    db.commit()
    return {"item": inventory_service.view(db, item), "history": rows}


@router.post("/{item_id}/restock")
def restock(item_id: int, body: StockAdjustment, ctx: Ctx = Depends(require_permission("edit_prices")), db: Session = Depends(get_db)):
    item = _item(db, ctx, item_id)
    entry = inventory_service.restock(db, item, body.quantity, ctx.user.id, body.note)
    activity_service.log(db, business_id=ctx.business_id, actor_user_id=ctx.user.id, action="inventory.restock", entity="catalog_item", entity_id=item.id, detail=f"+{body.quantity}")
    db.commit()
    sheet_sync_service.enqueue_sync(db, ctx.business_id)
    return {"item": inventory_service.view(db, item), "movement": _log(entry)}


@router.post("/{item_id}/count")
def count_stock(item_id: int, body: StockAdjustment, ctx: Ctx = Depends(require_permission("edit_prices")), db: Session = Depends(get_db)):
    item = _item(db, ctx, item_id)
    entry = inventory_service.count(db, item, body.quantity, ctx.user.id, body.note)
    activity_service.log(db, business_id=ctx.business_id, actor_user_id=ctx.user.id, action="inventory.count", entity="catalog_item", entity_id=item.id, detail=f"count={body.quantity}")
    db.commit()
    sheet_sync_service.enqueue_sync(db, ctx.business_id)
    return {"item": inventory_service.view(db, item), "movement": _log(entry)}

