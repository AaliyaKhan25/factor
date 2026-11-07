"""One business can never see or change another's data."""
from tests.conftest import member_id, new_owner, register


def test_owner_cannot_touch_another_businesses_members(client):
    owner_a, _ = new_owner(client, "a@example.com", "Shop A")
    owner_b, code_b = new_owner(client, "b@example.com", "Shop B")

    joiner = register(client, "joiner@example.com")
    client.post("/team/join", json={"code": code_b}, headers=joiner)
    mid = member_id(client, owner_b, "joiner@example.com")

    # Owner A cannot approve, reject, change or remove Owner B's member
    assert client.post(f"/team/members/{mid}/approve", json={}, headers=owner_a).status_code == 404
    assert client.post(f"/team/members/{mid}/reject", headers=owner_a).status_code == 404
    assert client.patch(f"/team/members/{mid}", json={}, headers=owner_a).status_code == 404
    assert client.delete(f"/team/members/{mid}", headers=owner_a).status_code == 404

    # ...and the request is untouched for the real owner
    rows = client.get("/team/members", headers=owner_b).json()
    assert next(r for r in rows if r["email"] == "joiner@example.com")["status"] == "pending"


def test_member_list_only_shows_your_own_business(client):
    owner_a, code_a = new_owner(client, "a@example.com", "Shop A")
    owner_b, _ = new_owner(client, "b@example.com", "Shop B")
    joiner = register(client, "joiner@example.com")
    client.post("/team/join", json={"code": code_a}, headers=joiner)

    emails_b = {r["email"] for r in client.get("/team/members", headers=owner_b).json()}
    assert emails_b == {"b@example.com"}


def test_a_code_only_ever_leads_to_its_own_business(client):
    owner_a, code_a = new_owner(client, "a@example.com", "Shop A")
    owner_b, _ = new_owner(client, "b@example.com", "Shop B")
    joiner = register(client, "joiner@example.com")
    client.post("/team/join", json={"code": code_a}, headers=joiner)
    mid = member_id(client, owner_a, "joiner@example.com")
    client.post(f"/team/members/{mid}/approve", json={}, headers=owner_a)

    assert client.get("/business", headers=joiner).json()["name"] == "Shop A"
