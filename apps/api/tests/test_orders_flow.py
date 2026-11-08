"""Status pipeline, evidence timeline, customers and business separation."""
from tests.conftest import new_owner
from tests.test_catalog_pricing import make_item, order


def go(client, owner, oid, status):
    return client.post(f"/orders/{oid}/status", json={"status": status}, headers=owner)


def test_full_pipeline_builds_the_timeline(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner)
    o = order(client, owner, item["id"]).json()
    assert o["code"] == "ORD-1001"
    for s in ("confirmed", "packed", "shipped", "delivered"):
        assert go(client, owner, o["id"], s).status_code == 200
    detail = client.get(f"/orders/{o['id']}", headers=owner).json()
    assert [e["kind"] for e in detail["events"]] == ["created", "confirmed", "packed", "shipped", "delivered"]
    assert detail["next_statuses"] == []


def test_steps_cannot_be_skipped_or_reversed(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner, quantity=5)
    o = order(client, owner, item["id"]).json()
    assert go(client, owner, o["id"], "shipped").status_code == 409     # skipped steps
    go(client, owner, o["id"], "confirmed")
    assert go(client, owner, o["id"], "confirmed").status_code == 409   # repeat
    go(client, owner, o["id"], "cancelled")
    assert go(client, owner, o["id"], "packed").status_code == 409       # cancelled is final


def test_shipped_orders_cannot_be_cancelled(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner)
    o = order(client, owner, item["id"]).json()
    for s in ("confirmed", "packed", "shipped"):
        go(client, owner, o["id"], s)
    assert go(client, owner, o["id"], "cancelled").status_code == 409


def test_same_phone_is_the_same_customer(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner, quantity=5)
    a = order(client, owner, item["id"]).json()
    b = order(client, owner, item["id"], customer={"name": "Riya S", "phone": "090000 00001"}).json()
    assert a["customer"]["id"] == b["customer"]["id"]
    assert b["code"] == "ORD-1002"


def test_businesses_cannot_see_each_others_orders_or_items(client):
    owner_a, _ = new_owner(client, "a@example.com", "Shop A")
    owner_b, _ = new_owner(client, "b@example.com", "Shop B")
    item_a = make_item(client, owner_a)
    o = order(client, owner_a, item_a["id"]).json()

    assert client.get(f"/orders/{o['id']}", headers=owner_b).status_code == 404
    assert go(client, owner_b, o["id"], "confirmed").status_code == 404
    assert client.get("/orders", headers=owner_b).json() == []
    assert client.get("/catalog", headers=owner_b).json() == []
    assert client.patch(f"/catalog/{item_a['id']}", json={"price_paise": 1}, headers=owner_b).status_code == 404
    # and B cannot order A's item
    assert order(client, owner_b, item_a["id"]).status_code == 404


def test_a_helper_without_manage_orders_cannot_create_or_move_orders(client):
    from tests.conftest import member_id, register
    owner, code = new_owner(client)
    item = make_item(client, owner)
    o = order(client, owner, item["id"]).json()
    helper = register(client, "helper@example.com")
    client.post("/team/join", json={"code": code}, headers=helper)
    client.post(f"/team/members/{member_id(client, owner, 'helper@example.com')}/approve", json={"preset": "helper"}, headers=owner)

    assert client.get("/orders", headers=helper).status_code == 200        # helper may view
    assert go(client, helper, o["id"], "confirmed").status_code == 403      # but not change
    assert order(client, helper, item["id"]).status_code == 403
