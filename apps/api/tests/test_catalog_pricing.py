"""Price comes from the catalog only. The client cannot set or change it on an order."""
from tests.conftest import new_owner, register


def make_item(client, owner, **kw):
    body = {"name": "Sage tote", "kind": "ready_stock", "price_paise": 85000, "quantity": 3}
    body.update(kw)
    r = client.post("/catalog", json=body, headers=owner)
    assert r.status_code == 201, r.text
    return r.json()


def order(client, owner, item_id, qty=1, **extra):
    body = {"customer": {"name": "Riya", "phone": "+91 90000 00001"}, "items": [{"catalog_item_id": item_id, "quantity": qty}]}
    body.update(extra)
    return client.post("/orders", json=body, headers=owner)


def test_total_is_computed_from_the_catalog(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner)
    r = order(client, owner, item["id"], qty=2)
    assert r.status_code == 201
    assert r.json()["total_paise"] == 170000
    assert r.json()["items"][0]["unit_price_paise"] == 85000


def test_the_client_cannot_send_a_price(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner)
    body = {
        "customer": {"name": "Riya"},
        "items": [{"catalog_item_id": item["id"], "quantity": 1, "unit_price_paise": 1}],
    }
    assert client.post("/orders", json=body, headers=owner).status_code == 422


def test_price_change_does_not_rewrite_old_orders(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner)
    first = order(client, owner, item["id"]).json()
    client.patch(f"/catalog/{item['id']}", json={"price_paise": 99000}, headers=owner)
    second = order(client, owner, item["id"]).json()
    assert client.get(f"/orders/{first['id']}", headers=owner).json()["total_paise"] == 85000
    assert second["total_paise"] == 99000


def test_item_fields_must_match_its_kind(client):
    owner, _ = new_owner(client)
    bad_stock = {"name": "x", "kind": "ready_stock", "price_paise": 100}
    bad_made = {"name": "x", "kind": "made_to_order", "price_paise": 100, "quantity": 2}
    assert client.post("/catalog", json=bad_stock, headers=owner).status_code == 422
    assert client.post("/catalog", json=bad_made, headers=owner).status_code == 422
    assert client.post("/catalog", json={**bad_stock, "price_paise": -5, "quantity": 1}, headers=owner).status_code == 422


def test_only_people_with_edit_prices_can_change_the_catalog(client):
    owner, code = new_owner(client)
    helper = register(client, "helper@example.com")
    client.post("/team/join", json={"code": code}, headers=helper)
    rows = client.get("/team/members", headers=owner).json()
    mid = next(r["id"] for r in rows if r["email"] == "helper@example.com")
    client.post(f"/team/members/{mid}/approve", json={"preset": "helper"}, headers=owner)

    assert client.get("/catalog", headers=helper).status_code == 200
    r = client.post("/catalog", json={"name": "x", "kind": "ready_stock", "price_paise": 1, "quantity": 1}, headers=helper)
    assert r.status_code == 403
