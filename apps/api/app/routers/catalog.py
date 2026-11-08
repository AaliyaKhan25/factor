"""Catalog: what you sell, the price, and how much is left."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Ctx, get_ctx, require_permission
from ..models.catalog_item import CatalogItem
from ..schemas.catalog import CatalogCreate, CatalogUpdate
from ..services import activity_service, order_service

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _view(db: Session, i: CatalogItem) -> dict:
    return {
        "id": i.id,
        "name": i.name,
        "kind": i.kind,
        "price_paise": i.price_paise,
        "quantity": i.quantity,
        "capacity": i.capacity,
        "lead_time_days": i.lead_time_days,
        "active": i.active,
        "available": order_service.availability(db, i),
    }


def _scoped(db: Session, ctx: Ctx, item_id: int) -> CatalogItem:
    i = db.get(CatalogItem, item_id)
    if i is None or i.business_id != ctx.business_id:
        raise HTTPException(status_code=404, detail="Item not found")
    return i


@router.get("")
def list_items(ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(CatalogItem).where(CatalogItem.business_id == ctx.business_id, CatalogItem.active.is_(True)).order_by(CatalogItem.id)
    ).all()
    return [_view(db, i) for i in rows]


@router.post("", status_code=201)
def create_item(body: CatalogCreate, ctx: Ctx = Depends(require_permission("edit_prices")), db: Session = Depends(get_db)):
    item = CatalogItem(business_id=ctx.business_id, **body.model_dump())
    db.add(item)
    db.flush()
    activity_service.log(
        db, business_id=ctx.business_id, actor_user_id=ctx.user.id, action="catalog.create", entity="catalog_item", entity_id=item.id
    )
    db.commit()
    return _view(db, item)


@router.patch("/{item_id}")
def update_item(
    item_id: int, body: CatalogUpdate, ctx: Ctx = Depends(require_permission("edit_prices")), db: Session = Depends(get_db)
):
    item = _scoped(db, ctx, item_id)
    changes = body.model_dump(exclude_unset=True)
    if "quantity" in changes and item.kind != "ready_stock":
        raise HTTPException(status_code=422, detail="Quantity is only for ready stock items")
    if "capacity" in changes and item.kind != "made_to_order":
        raise HTTPException(status_code=422, detail="Capacity is only for made-to-order items")
    for key, value in changes.items():
        if value is None and key != "lead_time_days":
            continue
        setattr(item, key, value)
    activity_service.log(
        db,
        business_id=ctx.business_id,
        actor_user_id=ctx.user.id,
        action="catalog.update",
        entity="catalog_item",
        entity_id=item.id,
        detail=",".join(sorted(changes)),
    )
    db.commit()
    return _view(db, item)
