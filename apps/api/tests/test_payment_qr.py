"""Signed, amount specific UPI QR payment pages."""
from tests.conftest import new_owner
from tests.test_catalog_pricing import make_item, order


def _shop_with_upi(client, session_factory):
    owner, _ = new_owner(client)
    with session_factory() as db:
        from app.models.business import Business
        business = db.query(Business).one()
        business.upi_id = "factor.shop@upi"
        db.commit()
    item = make_item(client, owner)
    return owner, item


def test_order_confirmation_exposes_signed_upi_payment_page(client, session_factory):
    owner, item = _shop_with_upi(client, session_factory)
    created = order(client, owner, item["id"], customer={"name": "Riya", "phone": "9000000001"}).json()
    assert created["payment"]["upi_ready"] is True
    assert "pa=factor.shop%40upi" in created["payment"]["upi_uri"]
    assert "am=850.00" in created["payment"]["upi_uri"]

    confirmed = client.post(f"/orders/{created['id']}/status", headers=owner, json={"status": "confirmed"})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["payment_delivery"]["status"] == "ready_to_share"
    link = confirmed.json()["payment"]["payment_link"]
    signature = link.split("signature=")[1]
    page = client.get(f"/payments/public/{created['id']}", params={"signature": signature})
    assert page.status_code == 200
    assert page.json()["total_paise"] == 85000
    assert page.json()["payee_name"]
    qr = client.get(f"/payments/public/{created['id']}/qr", params={"signature": signature})
    assert qr.status_code == 200
    assert qr.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in qr.content
    png = client.get(f"/payments/public/{created['id']}/qr.png", params={"signature": signature})
    assert png.status_code == 200
    assert png.headers["content-type"] == "image/png"
    assert png.content.startswith(b"\x89PNG")


def test_public_payment_and_qr_require_valid_signature(client, session_factory):
    owner, item = _shop_with_upi(client, session_factory)
    created = order(client, owner, item["id"]).json()
    invalid = "0" * 64
    assert client.get(f"/payments/public/{created['id']}", params={"signature": invalid}).status_code == 404
    assert client.get(f"/payments/public/{created['id']}/qr", params={"signature": invalid}).status_code == 404


def test_owner_can_edit_payee_and_upi_details(client):
    owner, _ = new_owner(client)
    saved = client.patch("/business", headers=owner, json={"name": "Riya Studio", "upi_id": "riya.studio@upi"})
    assert saved.status_code == 200, saved.text
    assert saved.json()["name"] == "Riya Studio"
    assert saved.json()["upi_id"] == "riya.studio@upi"
    assert client.get("/business", headers=owner).json()["upi_id"] == "riya.studio@upi"


def test_pending_payments_lists_link_and_qr(client, session_factory):
    owner, item = _shop_with_upi(client, session_factory)
    created = order(client, owner, item["id"]).json()
    rows = client.get("/payments/pending", headers=owner)
    assert rows.status_code == 200
    payment = next(row for row in rows.json() if row["id"] == created["id"])
    assert payment["payment_link"] and payment["qr_path"]


def test_order_confirmation_sends_qr_image_to_customer_phone(client, session_factory, monkeypatch):
    from types import SimpleNamespace
    from app.services import payment_service

    owner, item = _shop_with_upi(client, session_factory)
    created = order(client, owner, item["id"], customer={"name": "Riya", "phone": "9000000001"}).json()
    monkeypatch.setattr(payment_service, "settings", SimpleNamespace(
        jwt_secret="test-secret", public_app_url="https://factor.example", public_api_url="https://api.factor.example",
        whatsapp_token="token", whatsapp_phone_id="phone-id", meta_graph_api_version="v27.0"))
    sent = {}

    class Accepted:
        def raise_for_status(self):
            return None

    def fake_post(url, *, headers, json, timeout):
        sent.update(url=url, headers=headers, payload=json)
        return Accepted()

    monkeypatch.setattr(payment_service.httpx, "post", fake_post)
    confirmed = client.post(f"/orders/{created['id']}/status", headers=owner, json={"status": "confirmed"})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["payment_delivery"]["status"] == "accepted_by_whatsapp"
    assert sent["payload"]["to"] == "919000000001"
    assert sent["payload"]["type"] == "image"
    assert "/qr.png?signature=" in sent["payload"]["image"]["link"]


def test_dm_order_booking_shows_qr_on_its_linked_order(client, session_factory):
    owner, item = _shop_with_upi(client, session_factory)
    created = client.post("/inbox/simulate", headers=owner, json={
        "channel": "whatsapp", "handle": "+91 90000 00001", "name": "Riya", "text": "1 Sage tote confirm",
    })
    assert created.status_code == 201, created.text
    conversation = created.json()
    assert len(conversation["orders"]) == 1
    order = conversation["orders"][0]
    assert order["payment"]["upi_ready"]
    assert "/payments/public/" in order["payment"]["qr_path"] and "signature=" in order["payment"]["qr_path"]
    detail = client.get(f"/inbox/conversations/{conversation['id']}", headers=owner).json()
    assert detail["orders"][0]["payment"]["payment_link"]
    assert any("UPI QR is attached" in message["text"] for message in detail["messages"])


def test_instagram_dm_order_sends_image_attachment_when_sender_is_configured(client, session_factory, monkeypatch):
    from types import SimpleNamespace
    from app.services import payment_service

    owner, _ = _shop_with_upi(client, session_factory)
    monkeypatch.setattr(payment_service, "settings", SimpleNamespace(
        jwt_secret="test-secret", public_app_url="https://factor.example", public_api_url="https://api.factor.example",
        whatsapp_token="", whatsapp_phone_id="", instagram_access_token="ig-token", instagram_account_id="ig-account",
        meta_graph_api_version="v27.0"))
    sent = {}

    class Accepted:
        def raise_for_status(self):
            return None

    def fake_post(url, *, headers, json, timeout):
        sent.update(url=url, headers=headers, payload=json)
        return Accepted()

    monkeypatch.setattr(payment_service.httpx, "post", fake_post)
    response = client.post("/inbox/simulate", headers=owner, json={
        "channel": "instagram", "handle": "17890000000001", "name": "Riya", "text": "1 Sage tote confirm",
    })
    assert response.status_code == 201, response.text
    assert sent["payload"]["recipient"]["id"] == "17890000000001"
    assert sent["payload"]["message"]["attachment"]["type"] == "image"
    assert "/qr.png?signature=" in sent["payload"]["message"]["attachment"]["payload"]["url"]
