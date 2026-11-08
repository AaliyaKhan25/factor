"""Overview numbers come from real orders and chats."""
from tests.conftest import new_owner
from tests.test_catalog_pricing import make_item, order
from tests.test_inbox_agent import dm


def test_empty_business_shows_zeros(client):
    owner, _ = new_owner(client)
    d = client.get("/dashboard", headers=owner).json()
    assert d["sales_month_paise"] == 0 and d["orders_to_fulfil"] == 0 and d["messages_open"] == 0
    assert d["todo"] == [] and len(d["daily"]) == 28


def test_numbers_follow_orders_and_chats(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner, quantity=10)
    a = order(client, owner, item["id"], qty=2).json()
    order(client, owner, item["id"], qty=1)
    for s in ("confirmed", "packed"):
        client.post(f"/orders/{a['id']}/status", json={"status": s}, headers=owner)
    dm(client, owner, "custom bag please")

    d = client.get("/dashboard", headers=owner).json()
    assert d["sales_month_paise"] == 3 * 85000
    assert d["orders_to_fulfil"] == 2 and d["ready_to_ship"] == 1 and d["in_progress"] == 1
    assert d["unpaid_count"] == 2 and d["unpaid_paise"] == 3 * 85000
    assert d["messages_open"] == 1
    assert d["daily"][-1]["total_paise"] == 3 * 85000
    assert {t["kind"] for t in d["todo"]} == {"inbox", "orders", "payments", "ship"}


def test_cancelled_orders_do_not_count_as_sales(client):
    owner, _ = new_owner(client)
    item = make_item(client, owner)
    o = order(client, owner, item["id"]).json()
    client.post(f"/orders/{o['id']}/status", json={"status": "cancelled"}, headers=owner)
    assert client.get("/dashboard", headers=owner).json()["sales_month_paise"] == 0


def test_dashboard_is_per_business(client):
    owner_a, _ = new_owner(client, "a@example.com", "Shop A")
    owner_b, _ = new_owner(client, "b@example.com", "Shop B")
    item = make_item(client, owner_a)
    order(client, owner_a, item["id"])
    assert client.get("/dashboard", headers=owner_b).json()["sales_month_paise"] == 0
