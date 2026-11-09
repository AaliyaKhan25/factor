"""Inventory ledger and seller-owned courier webhook coverage."""
import hashlib
import hmac
import json
import time

from cryptography.fernet import Fernet

from tests.conftest import new_owner


def create_item(client, headers, quantity=15):
    return client.post("/catalog", json={"name": "Woven bag", "kind": "ready_stock",
        "price_paise": 12000, "quantity": quantity}, headers=headers).json()


def test_inventory_ledger_tracks_order_sale_cancel_restock_and_count(client):
    owner, _ = new_owner(client)
    item = create_item(client, owner)
    created = client.post("/orders", headers=owner, json={"customer": {"name": "Mira"},
        "items": [{"catalog_item_id": item["id"], "quantity": 1}]}).json()
    assert client.get("/inventory", headers=owner).json()["items"][0]["quantity"] == 14
    client.post(f"/orders/{created['id']}/status", headers=owner, json={"status": "cancelled"})
    client.post(f"/inventory/{item['id']}/restock", headers=owner, json={"quantity": 5, "note": "New batch"})
    client.post(f"/inventory/{item['id']}/count", headers=owner, json={"quantity": 17})
    view = client.get(f"/inventory/{item['id']}/history", headers=owner).json()
    assert view["item"]["quantity"] == 17
    assert {entry["kind"] for entry in view["history"]} == {"opening", "sale", "cancellation", "restock", "count"}
    assert all(entry["balance_after"] is not None for entry in view["history"])


def test_signed_courier_webhook_matches_awb_and_deduplicates(client, monkeypatch):
    monkeypatch.setenv("COURIER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    owner, _ = new_owner(client)
    item = create_item(client, owner)
    order = client.post("/orders", headers=owner, json={"customer": {"name": "Mira"},
        "items": [{"catalog_item_id": item["id"], "quantity": 1}]}).json()
    connection = client.post("/couriers", headers=owner, json={"name": "Sample Courier", "provider": "fake",
        "credentials": {"next_status": "In Transit"}})
    assert connection.status_code == 201, connection.text
    conn = connection.json()
    shipment = client.put(f"/couriers/orders/{order['id']}/shipment", headers=owner, json={
        "courier_name": "Sample Courier", "awb": "AWB-77", "courier_connection_id": conn["id"]})
    assert shipment.status_code == 200
    raw = json.dumps({"event_id": "evt-1", "awb": "AWB-77", "order_code": "wrong-code",
        "status": "In Transit", "detail": "Reached hub"}, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(conn["webhook_secret"].encode(), timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    headers = {"X-Courier-Timestamp": timestamp, "X-Courier-Signature": f"sha256={signature}",
        "Content-Type": "application/json"}
    response = client.post(conn["webhook_path"], content=raw, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["order_code"] == order["code"]  # AWB wins over a wrong order code
    duplicate = client.post(conn["webhook_path"], content=raw, headers=headers)
    assert duplicate.status_code == 200 and duplicate.json()["duplicate"] is True
    detail = client.get(f"/orders/{order['id']}", headers=owner).json()
    assert detail["tracking"]["status"] == "in_transit"
    assert any(event["kind"] == "courier_update" for event in detail["events"])


def test_courier_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setenv("COURIER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    owner, _ = new_owner(client)
    conn = client.post("/couriers", headers=owner, json={"name": "Sample", "provider": "generic"}).json()
    response = client.post(conn["webhook_path"], json={"event_id": "x", "awb": "x", "status": "delivered"},
        headers={"X-Courier-Timestamp": str(int(time.time())), "X-Courier-Signature": "sha256=bad"})
    assert response.status_code == 401
