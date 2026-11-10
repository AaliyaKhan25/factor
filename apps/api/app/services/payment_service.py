"""UPI payment links, amount-specific QR data, and optional WhatsApp delivery."""
import hashlib
import hmac
from io import BytesIO
import struct
import zlib
from urllib.parse import urlencode

import httpx
import qrcode
from qrcode.image.svg import SvgPathImage
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models.business import Business
from ..models.conversation import Conversation
from ..models.customer import Customer
from ..models.order import Order
from ..models.order_item import OrderItem
from ..services import activity_service, conversation_service


def signature(order: Order) -> str:
    payload = f"payment:{order.business_id}:{order.id}:{order.code}".encode()
    return hmac.new(settings.jwt_secret.encode(), payload, hashlib.sha256).hexdigest()


def valid_signature(order: Order, supplied: str) -> bool:
    return hmac.compare_digest(signature(order), supplied)


def upi_uri(business: Business, order: Order) -> str:
    if not business.upi_id or not business.upi_id.strip():
        return ""
    params = urlencode({
        "pa": business.upi_id.strip(),
        "pn": business.name.strip(),
        "am": f"{order.total_paise / 100:.2f}",
        "cu": "INR",
        "tn": f"Order {order.code}"[:80],
    })
    return f"upi://pay?{params}"


def payment_view(db: Session, order: Order) -> dict:
    business = db.get(Business, order.business_id)
    uri = upi_uri(business, order) if business else ""
    key = signature(order)
    return {
        "upi_ready": bool(uri),
        "payee_name": business.name if business else "",
        "upi_id": business.upi_id if business else None,
        "amount_paise": order.total_paise,
        "upi_uri": uri or None,
        "payment_link": f"{settings.public_app_url}/pay/{order.id}?signature={key}" if uri else None,
        "qr_path": f"/payments/public/{order.id}/qr?signature={key}" if uri else None,
    }


def public_details(db: Session, order: Order, supplied_signature: str) -> dict:
    if not valid_signature(order, supplied_signature):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Payment page not found")
    business = db.get(Business, order.business_id)
    lines = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id)).all()
    payment = payment_view(db, order)
    return {
        "business_name": business.name if business else "",
        "order_code": order.code,
        "order_status": order.status,
        "payment_status": order.payment_status,
        "items": [{"name": line.name, "quantity": line.quantity, "unit_price_paise": line.unit_price_paise} for line in lines],
        "total_paise": order.total_paise,
        **payment,
    }


def qr_svg(db: Session, order: Order, supplied_signature: str) -> bytes:
    if not valid_signature(order, supplied_signature):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Payment QR not found")
    business = db.get(Business, order.business_id)
    uri = upi_uri(business, order) if business else ""
    if not uri:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Add a UPI ID to your business settings first")
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    return qr.make_image(image_factory=SvgPathImage).to_string(encoding="utf-8")


def qr_png(db: Session, order: Order, supplied_signature: str) -> bytes:
    if not valid_signature(order, supplied_signature):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Payment QR not found")
    business = db.get(Business, order.business_id)
    uri = upi_uri(business, order) if business else ""
    if not uri:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Add a UPI ID to your business settings first")
    scale = 10
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=scale, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    width = len(matrix) * scale
    scanlines = bytearray()
    for row in matrix:
        pixels = b"".join((b"\x00\x00\x00" if dark else b"\xff\xff\xff") * scale for dark in row)
        for _ in range(scale):
            scanlines.append(0)  # PNG filter: None
            scanlines.extend(pixels)

    def chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xffffffff)

    buffer = BytesIO()
    buffer.write(b"\x89PNG\r\n\x1a\n")
    buffer.write(chunk(b"IHDR", struct.pack(">IIBBBBB", width, width, 8, 2, 0, 0, 0)))
    buffer.write(chunk(b"IDAT", zlib.compress(bytes(scanlines), level=9)))
    buffer.write(chunk(b"IEND", b""))
    return buffer.getvalue()


def pending_orders(db: Session, business_id: int) -> list[dict]:
    rows = db.scalars(select(Order).where(
        Order.business_id == business_id,
        Order.status != "cancelled",
        Order.payment_status != "paid",
    ).order_by(Order.created_at.desc())).all()
    result = []
    for order in rows:
        customer = db.get(Customer, order.customer_id)
        result.append({
            "id": order.id, "code": order.code, "status": order.status,
            "payment_status": order.payment_status, "total_paise": order.total_paise,
            "customer_name": customer.name if customer else "Customer", "created_at": order.created_at,
            **payment_view(db, order),
        })
    return result


def notify_customer(db: Session, order: Order) -> dict:
    """Send the signed QR over the order's connected messaging channel when configured."""
    payment = payment_view(db, order)
    if not payment["upi_ready"]:
        return {"status": "needs_upi", "message": "Add the business UPI ID before sending a payment request."}
    conversation = db.scalar(select(Conversation).where(
        Conversation.business_id == order.business_id,
        Conversation.customer_id == order.customer_id,
    ).order_by(Conversation.last_message_at.desc()).limit(1))
    customer = db.get(Customer, order.customer_id)
    channel = conversation.channel if conversation else "whatsapp"
    if channel == "whatsapp" and settings.whatsapp_token and settings.whatsapp_phone_id:
        access_token = settings.whatsapp_token
        sender_id = settings.whatsapp_phone_id
    elif channel == "instagram" and settings.instagram_access_token and settings.instagram_account_id:
        access_token = settings.instagram_access_token
        sender_id = settings.instagram_account_id
    else:
        activity_service.log(db, business_id=order.business_id, actor_user_id=order.created_by,
                             action="payment.link_ready", entity="order", entity_id=order.id,
                             detail=f"No {channel} sender configured; the payment page is ready to share manually.")
        db.commit()
        return {"status": "ready_to_share", "payment_link": payment["payment_link"],
                "message": f"Payment QR is ready on the order. Connect {channel.title()} sending to deliver it to the customer."}

    recipient = (conversation.handle if conversation else (customer.phone if customer else "")) if channel == "whatsapp" else (conversation.handle if conversation else "")
    to = "".join(c for c in recipient if c.isdigit())
    if channel == "whatsapp":
        if len(to) == 10:
            to = "91" + to
        if len(to) < 10:
            return {"status": "ready_to_share", "payment_link": payment["payment_link"],
                    "message": "Customer WhatsApp number is missing; payment QR is ready on the order."}
    elif not recipient:
        return {"status": "ready_to_share", "payment_link": payment["payment_link"],
                "message": "Customer account ID is missing; payment QR is ready on the order."}
    text = f"Payment for order {order.code} · ₹{order.total_paise / 100:.2f}. Scan this QR to pay, or open: {payment['payment_link']}"
    url = f"https://graph.facebook.com/{settings.meta_graph_api_version}/{sender_id}/messages"
    image_url = f"{settings.public_api_url}/payments/public/{order.id}/qr.png?signature={signature(order)}"
    if channel == "whatsapp":
        payload = {"messaging_product": "whatsapp", "to": to, "type": "image",
                   "image": {"link": image_url, "caption": text}}
    else:
        payload = {"recipient": {"id": recipient}, "message": {"attachment": {
            "type": "image", "payload": {"url": image_url, "is_reusable": False}}}}
    try:
        response = httpx.post(url, headers={"Authorization": f"Bearer {access_token}"}, json=payload, timeout=12)
        response.raise_for_status()
    except (httpx.HTTPError, ValueError) as exc:
        activity_service.log(db, business_id=order.business_id, actor_user_id=order.created_by,
                             action="payment.send_failed", entity="order", entity_id=order.id,
                             detail=str(exc)[:450])
        db.commit()
        return {"status": "failed", "payment_link": payment["payment_link"],
                "message": f"{channel.title()} did not accept the payment QR. The link is available to share manually."}

    if conversation:
        conversation_service.add_message(db, conversation, "out", "agent", text)
    activity_service.log(db, business_id=order.business_id, actor_user_id=order.created_by,
                         action="payment.link_sent", entity="order", entity_id=order.id,
                         detail=f"{channel.title()} accepted a payment QR for {order.code}.")
    db.commit()
    return {"status": f"accepted_by_{channel}", "payment_link": payment["payment_link"],
            "message": f"{channel.title()} accepted the payment QR for delivery."}
