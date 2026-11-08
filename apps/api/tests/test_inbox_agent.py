"""The agent answers what it can from the catalog and hands everything else to the owner."""
from tests.conftest import member_id, new_owner, register
from tests.test_catalog_pricing import make_item


def dm(client, owner, text, handle="@riya.knits", channel="instagram", name="Riya"):
    r = client.post("/inbox/simulate", json={"channel": channel, "handle": handle, "name": name, "text": text}, headers=owner)
    assert r.status_code == 201, r.text
    return r.json()


def last_reply(conv):
    return [m for m in conv["messages"] if m["sender"] == "agent"][-1]["text"]


def setup(client):
    owner, code = new_owner(client)
    tote = make_item(client, owner, name="Sage green tote", quantity=3)
    bunny = make_item(client, owner, name="Amigurumi bunny", kind="made_to_order", quantity=None, capacity=5, lead_time_days=7, price_paise=60000)
    return owner, code, tote, bunny


def test_price_question_gets_the_exact_catalog_price(client):
    owner, *_ = setup(client)
    c = dm(client, owner, "hi, how much is the sage green tote?")
    assert c["status"] == "agent"
    assert "Rs 850 each" in last_reply(c)
    assert "3 available" in last_reply(c)


def test_made_to_order_quote_mentions_lead_time(client):
    owner, *_ = setup(client)
    c = dm(client, owner, "price of bunny?")
    assert "Rs 600" in last_reply(c) and "7 days" in last_reply(c)


def test_confirm_books_an_order_and_takes_stock(client):
    owner, _, tote, _ = setup(client)
    c = dm(client, owner, "2 tote chahiye, confirm")
    assert c["status"] == "agent"
    assert "ORD-1001" in last_reply(c) and "Rs 1,700" in last_reply(c)
    orders = client.get("/orders", headers=owner).json()
    assert len(orders) == 1 and orders[0]["source"] == "instagram" and orders[0]["total_paise"] == 170000
    item = next(i for i in client.get("/catalog", headers=owner).json() if i["id"] == tote["id"])
    assert item["available"] == 1
    assert c["orders"][0]["code"] == "ORD-1001"


def test_cannot_book_more_than_is_available(client):
    owner, *_ = setup(client)
    c = dm(client, owner, "5 tote chahiye")
    assert "only have 3" in last_reply(c)
    assert client.get("/orders", headers=owner).json() == []


def test_unavailable_item_is_not_sold(client):
    owner, _, tote, _ = setup(client)
    client.patch(f"/catalog/{tote['id']}", json={"quantity": 0}, headers=owner)
    c = dm(client, owner, "tote confirm")
    assert "not available" in last_reply(c)
    assert client.get("/orders", headers=owner).json() == []


def test_things_the_agent_must_not_handle_go_to_the_owner(client):
    owner, *_ = setup(client)
    cases = {
        "can you make a bag with my dog's name on it": "Custom request",
        "bhaiya thoda kam karo price": "Wants to bargain",
        "order not delivered i want a refund": "Complaint or return",
        "payment done, sending screenshot": "Payment claim to verify",
        "asdf": "Not sure what they need",
    }
    for i, (text, reason) in enumerate(cases.items()):
        c = dm(client, owner, text, handle=f"@user{i}")
        assert c["status"] == "needs_owner", text
        assert c["reason"] == reason, text


def test_agent_stays_quiet_once_the_owner_has_the_chat(client):
    owner, *_ = setup(client)
    c = dm(client, owner, "custom bag please")
    n = len(c["messages"])
    c = dm(client, owner, "hello? how much is the tote")
    assert len(c["messages"]) == n + 1            # only the customer's message was added
    assert c["status"] == "needs_owner"


def test_owner_can_reply_then_close_or_hand_back(client):
    owner, *_ = setup(client)
    c = dm(client, owner, "custom bag please")
    r = client.post(f"/inbox/conversations/{c['id']}/reply", json={"text": "Sure, what size?"}, headers=owner).json()
    assert r["messages"][-1]["sender"] == "owner"
    r = client.post(f"/inbox/conversations/{c['id']}/status", json={"status": "resolved"}, headers=owner).json()
    assert r["status"] == "resolved"
    c = dm(client, owner, "price of tote?")           # a new message re-opens it for the agent
    assert c["status"] == "agent" and "Rs 850" in last_reply(c)


def test_buckets_and_counts_update(client):
    owner, *_ = setup(client)
    dm(client, owner, "price of tote?", handle="@a")
    dm(client, owner, "custom please", handle="@b")
    assert client.get("/inbox/counts", headers=owner).json() == {"needs_owner": 1, "agent": 1, "resolved": 0}
    assert [c["handle"] for c in client.get("/inbox/conversations?bucket=needs_owner", headers=owner).json()] == ["@b"]
    assert [c["handle"] for c in client.get("/inbox/conversations?bucket=agent", headers=owner).json()] == ["@a"]


def test_whatsapp_chat_uses_the_phone_number_as_the_customer(client):
    owner, *_ = setup(client)
    dm(client, owner, "tote confirm", handle="+91 90000 00001", channel="whatsapp")
    dm(client, owner, "tote confirm", handle="+919000000001", channel="whatsapp")      # same person, other spelling
    customers = client.get("/customers", headers=owner).json()
    assert len(customers) == 1 and customers[0]["phone"] == "9000000001" and customers[0]["orders"] == 2


def test_chats_are_separate_per_business(client):
    owner_a, *_ = setup(client)
    owner_b, _ = new_owner(client, "b@example.com", "Shop B")
    c = dm(client, owner_a, "custom bag")
    assert client.get(f"/inbox/conversations/{c['id']}", headers=owner_b).status_code == 404
    assert client.post(f"/inbox/conversations/{c['id']}/reply", json={"text": "x"}, headers=owner_b).status_code == 404
    assert client.get("/inbox/conversations", headers=owner_b).json() == []
    # B's agent knows nothing about A's catalog
    c2 = dm(client, owner_b, "price of tote?")
    assert c2["status"] == "needs_owner" and c2["reason"] == "No catalog items set up yet"


def test_inbox_needs_the_reply_permission(client):
    owner, code, *_ = setup(client)
    packer = register(client, "packer@example.com")
    client.post("/team/join", json={"code": code}, headers=packer)
    client.post(f"/team/members/{member_id(client, owner, 'packer@example.com')}/approve", json={"preset": "packer"}, headers=owner)
    assert client.get("/inbox/conversations", headers=packer).status_code == 403
