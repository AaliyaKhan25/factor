"""Ready stock runs down, made-to-order has a cap on open orders, cancelling gives it back."""
from tests.conftest import new_owner
from tests.test_catalog_pricing import make_item, order


def stock(client, owner, item_id):
    return next(i for i in client.get("/catalog", headers=owner).json() if i["id"] == item_id)


def test_ready_stock_cannot_be_oversold(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner, quantity=2)
    assert order(client, owner, item["id"], qty=2).status_code == 201
    r = order(client, owner, item["id"], qty=1)
    assert r.status_code == 409
    assert "not available" in r.json()["detail"]


def test_error_tells_how_many_are_left(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner, quantity=2)
    r = order(client, owner, item["id"], qty=5)
    assert r.status_code == 409
    assert r.json()["detail"] == "Only 2 of Sage tote available"


def test_repeated_lines_are_added_together(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner, quantity=2)
    body = {
        "customer": {"name": "Riya"},
        "items": [{"catalog_item_id": item["id"], "quantity": 2}, {"catalog_item_id": item["id"], "quantity": 2}],
    }
    assert client.post("/orders", json=body, headers=owner).status_code == 409


def test_cancelling_returns_the_stock(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner, quantity=2)
    placed = order(client, owner, item["id"], qty=2).json()
    assert stock(client, owner, item["id"])["available"] == 0
    client.post(f"/orders/{placed['id']}/status", json={"status": "cancelled"}, headers=owner)
    assert stock(client, owner, item["id"])["available"] == 2


def test_made_to_order_is_capped_by_open_orders(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner, kind="made_to_order", quantity=None, capacity=3, lead_time_days=7)
    first = order(client, owner, item["id"], qty=2).json()
    assert order(client, owner, item["id"], qty=2).status_code == 409
    assert order(client, owner, item["id"], qty=1).status_code == 201

    # finishing an order frees its capacity
    for s in ("confirmed", "packed", "shipped", "delivered"):
        assert client.post(f"/orders/{first['id']}/status", json={"status": s}, headers=owner).status_code == 200
    assert order(client, owner, item["id"], qty=2).status_code == 201


def test_a_failed_order_changes_nothing(client):
    owner, _ = new_owner(client)
    a = make_item(client, owner, name="A", quantity=5)
    b = make_item(client, owner, name="B", quantity=1)
    body = {"customer": {"name": "Riya"}, "items": [
        {"catalog_item_id": a["id"], "quantity": 2}, {"catalog_item_id": b["id"], "quantity": 3}]}
    assert client.post("/orders", json=body, headers=owner).status_code == 409
    assert stock(client, owner, a["id"])["available"] == 5
    assert client.get("/orders", headers=owner).json() == []
