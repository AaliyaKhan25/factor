"""Voice order service integrating Gnani.ai Indic Speech recognition and automatic order creation."""
import logging
from typing import Any, Dict, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai import extractor, speech
from ..models.catalog_item import CatalogItem
from ..models.order import Order
from ..schemas.orders import CustomerIn, LineIn, OrderCreate
from ..services import activity_service, order_service

logger = logging.getLogger(__name__)


def process_voice_order(
    db: Session,
    business_id: int,
    actor_id: Optional[int],
    transcript: str,
    language: str = "en-IN",
) -> Dict[str, Any]:
    """Parse transcript from Gnani.ai and automatically create an order in the database."""
    if not transcript or not transcript.strip():
        raise ValueError("Empty voice transcript received")

    # 1. Parse natural language into structured order draft
    parsed = extractor.parse_voice_order(transcript)
    items_draft = parsed["items"]

    lines: list[LineIn] = []

    # 2. Match or auto-provision catalog items
    for it in items_draft:
        item_name = it["name"].strip()
        qty = max(it["quantity"], 1)
        unit_price = it["unit_price_paise"]

        # Search existing catalog items for this business
        catalog_item = db.scalar(
            select(CatalogItem).where(
                CatalogItem.business_id == business_id,
                func.lower(CatalogItem.name) == item_name.lower(),
            )
        )

        if not catalog_item:
            # Also try substring / singular match (e.g., 'roses' -> 'rose')
            base_word = item_name.rstrip("s").rstrip("es") if len(item_name) > 3 else item_name
            catalog_item = db.scalar(
                select(CatalogItem).where(
                    CatalogItem.business_id == business_id,
                    CatalogItem.name.ilike(f"%{base_word}%"),
                )
            )

        if not catalog_item:
            # Auto-create catalog item so voice creation is frictionless
            catalog_item = CatalogItem(
                business_id=business_id,
                name=item_name.capitalize(),
                kind="ready_stock",
                price_paise=unit_price if unit_price > 0 else 2000,
                quantity=qty,
                active=True,
            )
            db.add(catalog_item)
            db.flush()
        else:
            # If ready_stock has insufficient quantity for this voice order, restock it
            if catalog_item.kind == "ready_stock":
                current_qty = catalog_item.quantity or 0
                if current_qty < qty:
                    catalog_item.quantity = current_qty + qty

            # If unit price was zero in catalog but specified in voice, update it
            if catalog_item.price_paise == 0 and unit_price > 0:
                catalog_item.price_paise = unit_price

        lines.append(LineIn(catalog_item_id=catalog_item.id, quantity=qty))

    # 3. Create the order via order_service
    order_create = OrderCreate(
        customer=CustomerIn(
            name=parsed["customer"]["name"],
            phone=parsed["customer"]["phone"],
            handle=parsed["customer"]["handle"],
        ),
        source="voice",
        items=lines,
        note=f"Voice order via Gnani.ai: \"{transcript}\"",
    )

    order = order_service.create_order(db, business_id, actor_id, order_create)

    # 4. Log audit activity
    activity_service.log(
        db,
        business_id=business_id,
        actor_user_id=actor_id,
        action="order.voice_create",
        entity="order",
        entity_id=order.id,
        detail=f"Gnani.ai transcript: {transcript}",
    )

    db.commit()

    return {
        "success": True,
        "provider": "Gnani.ai",
        "transcript": transcript,
        "language": language,
        "parsed": parsed,
        "order": {
            "id": order.id,
            "code": order.code,
            "status": order.status,
            "payment_status": order.payment_status,
            "total_paise": order.total_paise,
            "customer_name": parsed["customer"]["name"],
            "created_at": order.created_at,
        },
    }
