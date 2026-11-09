"""Stock ledger operations. Ready-stock balances change only through recorded movements."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.catalog_item import CatalogItem
from ..models.stock_log import StockLog

LOW_STOCK_AT = 5


def record(db: Session, item: CatalogItem, *, kind: str, delta: int, balance: int, actor_id: int | None, note: str = "") -> StockLog:
    entry = StockLog(
        business_id=item.business_id,
        catalog_item_id=item.id,
        kind=kind,
        quantity_delta=delta,
        balance_after=balance,
        actor_user_id=actor_id,
        note=note.strip()[:240],
    )
    db.add(entry)
    return entry


def ensure_opening(db: Session, item: CatalogItem, actor_id: int | None = None, balance: int | None = None) -> None:
    if item.kind != "ready_stock":
        return
    exists = db.scalar(select(StockLog.id).where(StockLog.catalog_item_id == item.id).limit(1))
    if exists is None:
        qty = max(0, item.quantity or 0) if balance is None else max(0, balance)
        record(db, item, kind="opening", delta=qty, balance=qty, actor_id=actor_id, note="Opening stock")


def restock(db: Session, item: CatalogItem, quantity: int, actor_id: int, note: str = "") -> StockLog:
    if item.kind != "ready_stock":
        raise HTTPException(status_code=422, detail="Made-to-order items use capacity, not stock")
    if quantity < 1 or quantity > 100_000:
        raise HTTPException(status_code=422, detail="Restock quantity must be between 1 and 100,000")
    ensure_opening(db, item, actor_id)
    item.quantity = (item.quantity or 0) + quantity
    return record(db, item, kind="restock", delta=quantity, balance=item.quantity, actor_id=actor_id, note=note)


def count(db: Session, item: CatalogItem, quantity: int, actor_id: int, note: str = "") -> StockLog:
    if item.kind != "ready_stock":
        raise HTTPException(status_code=422, detail="Made-to-order items use capacity, not stock")
    if quantity < 0 or quantity > 100_000:
        raise HTTPException(status_code=422, detail="Count must be between 0 and 100,000")
    ensure_opening(db, item, actor_id)
    before = item.quantity or 0
    item.quantity = quantity
    return record(db, item, kind="count", delta=quantity - before, balance=quantity, actor_id=actor_id, note=note or "Physical stock count")


def history(db: Session, item: CatalogItem) -> list[StockLog]:
    ensure_opening(db, item)
    return db.scalars(
        select(StockLog).where(StockLog.catalog_item_id == item.id).order_by(StockLog.created_at.desc(), StockLog.id.desc())
    ).all()


def view(db: Session, item: CatalogItem) -> dict:
    from .order_service import availability, open_quantity

    if item.kind == "ready_stock":
        ensure_opening(db, item)
        quantity = item.quantity or 0
        return {
            "id": item.id,
            "name": item.name,
            "kind": item.kind,
            "quantity": quantity,
            "available": quantity,
            "low_stock_threshold": LOW_STOCK_AT,
            "low_stock": 0 < quantity <= LOW_STOCK_AT,
            "out_of_stock": quantity == 0,
            "price_paise": item.price_paise,
        }
    open_orders = open_quantity(db, item.business_id, item.id)
    return {
        "id": item.id,
        "name": item.name,
        "kind": item.kind,
        "capacity": item.capacity or 0,
        "open_orders": open_orders,
        "available": availability(db, item),
        "low_stock_threshold": None,
        "low_stock": False,
        "out_of_stock": False,
        "price_paise": item.price_paise,
    }
