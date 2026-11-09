"""One-way, debounced snapshots from Factor into three app-owned Google Sheet tabs."""
import threading
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from ..integrations import google_sheets
from ..models.catalog_item import CatalogItem
from ..models.customer import Customer
from ..models.order import Order
from ..models.order_item import OrderItem
from ..models.sheet_connection import SheetConnection
from ..models.stock_log import StockLog
from ..utils.time import utcnow

_timers: dict[int, threading.Timer] = {}
_timers_lock = threading.Lock()


def _iso(value) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat(timespec="seconds")


def build_tabs(db: Session, business_id: int) -> dict[str, list[list[str]]]:
    orders: list[list[str]] = [["Order code", "Created at (UTC)", "Customer", "Phone", "Items", "Status", "Payment", "Total (INR)"]]
    q = select(Order, Customer).join(Customer, Customer.id == Order.customer_id).where(Order.business_id == business_id).order_by(Order.id)
    for order, customer in db.execute(q).all():
        lines = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)).all()
        # All cell values are strings and sent with RAW, so customer-controlled values stay text.
        items = ", ".join(f"{line.quantity} x {line.name}" for line in lines)
        orders.append([order.code, _iso(order.created_at), customer.name, customer.phone or "", items,
                       order.status, order.payment_status, f"{order.total_paise / 100:.2f}"])

    inventory: list[list[str]] = [["Item", "Type", "On hand", "Open orders", "Capacity", "Price (INR)"]]
    for item in db.scalars(select(CatalogItem).where(CatalogItem.business_id == business_id).order_by(CatalogItem.id)).all():
        if item.kind == "ready_stock":
            inventory.append([item.name, item.kind, str(item.quantity or 0), "", "", f"{item.price_paise / 100:.2f}"])
        else:
            from .order_service import open_quantity
            inventory.append([item.name, item.kind, "", str(open_quantity(db, business_id, item.id)), str(item.capacity or 0), f"{item.price_paise / 100:.2f}"])

    stock: list[list[str]] = [["Date (UTC)", "Item", "Change", "Balance after", "Movement", "Note"]]
    qlog = select(StockLog, CatalogItem).join(CatalogItem, CatalogItem.id == StockLog.catalog_item_id).where(
        StockLog.business_id == business_id
    ).order_by(StockLog.id)
    for entry, item in db.execute(qlog).all():
        stock.append([_iso(entry.created_at), item.name, str(entry.quantity_delta), str(entry.balance_after), entry.kind, entry.note])
    return {"Orders": orders, "Inventory": inventory, "Stock log": stock}


def status(db: Session, business_id: int) -> dict:
    connection = db.scalar(select(SheetConnection).where(SheetConnection.business_id == business_id))
    return {
        "connected": connection is not None,
        "spreadsheet_url": connection.spreadsheet_url if connection else None,
        "last_synced_at": connection.last_synced_at if connection else None,
        "last_error": connection.last_error if connection else "",
        "server_configured": bool(settings.google_service_account_json),
        "service_account_email": _service_account_email(),
    }


def _service_account_email() -> str | None:
    import json
    if not settings.google_service_account_json:
        return None
    try:
        return json.loads(settings.google_service_account_json).get("client_email")
    except (ValueError, AttributeError):
        return None


def sync_business(db: Session, business_id: int) -> dict:
    connection = db.scalar(select(SheetConnection).where(SheetConnection.business_id == business_id))
    if connection is None:
        return {"ok": False, "error": "Connect a Google Sheet in Settings first"}
    try:
        google_sheets.write_snapshot(connection.spreadsheet_id, build_tabs(db, business_id))
        connection.last_synced_at = utcnow()
        connection.last_error = ""
        db.commit()
        return {"ok": True, "last_synced_at": connection.last_synced_at, "last_error": ""}
    except Exception as exc:
        connection.last_error = str(exc)[:500]
        db.commit()
        return {"ok": False, "last_synced_at": connection.last_synced_at, "error": connection.last_error}


def _run_scheduled(business_id: int) -> None:
    with _timers_lock:
        _timers.pop(business_id, None)
    db = SessionLocal()
    try:
        sync_business(db, business_id)
    finally:
        db.close()


def enqueue_sync(db: Session, business_id: int) -> None:
    """Coalesce rapid writes and push a fresh snapshot about three seconds later."""
    if not settings.google_service_account_json:
        return
    connected = db.scalar(select(SheetConnection.id).where(SheetConnection.business_id == business_id)) is not None
    if not connected:
        return
    with _timers_lock:
        old = _timers.pop(business_id, None)
        if old:
            old.cancel()
        timer = threading.Timer(3.0, _run_scheduled, args=(business_id,))
        timer.daemon = True
        _timers[business_id] = timer
        timer.start()
