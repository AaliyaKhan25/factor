"""Tests for Gnani.ai voice order parser and automatic order creation endpoint."""
from tests.conftest import new_owner
from app.ai.extractor import parse_voice_order


def test_extractor_user_prompt_case():
    parsed = parse_voice_order("rahul bought 80 roses , total price 1600")
    assert parsed["customer"]["name"] == "Rahul"
    assert len(parsed["items"]) == 1
    assert parsed["items"][0]["name"].lower() == "roses"
    assert parsed["items"][0]["quantity"] == 80
    assert parsed["total_price_paise"] == 160000
    assert parsed["items"][0]["unit_price_paise"] == 2000


def test_extractor_hindi_hinglish_variations():
    parsed = parse_voice_order("rahul ne 80 roses khareede, total price 1600 rupaye")
    assert parsed["customer"]["name"] == "Rahul"
    assert parsed["items"][0]["name"].lower() == "roses"
    assert parsed["items"][0]["quantity"] == 80
    assert parsed["total_price_paise"] == 160000

    parsed2 = parse_voice_order("customer ananya 9876543210 bought 2 bridal sets for 12400")
    assert parsed2["customer"]["name"] == "Ananya"
    assert parsed2["customer"]["phone"] == "9876543210"
    assert parsed2["items"][0]["quantity"] == 2
    assert parsed2["total_price_paise"] == 1240000


def test_voice_status_endpoint(client):
    r = client.get("/voice/status")
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "Gnani.ai"
    assert data["speech_to_text"] and data["text_to_speech"]
    assert data["supported_languages"][0]["code"] == "indic-auto"


def test_voice_command_creates_one_time_proposal_instead_of_order(client):
    owner, _ = new_owner(client)
    item = client.post("/catalog", json={"name": "Roses", "kind": "ready_stock", "price_paise": 2000, "quantity": 15}, headers=owner).json()
    proposed = client.post("/voice/commands", json={"text": "restock 4 to Roses"}, headers=owner)
    assert proposed.status_code == 200, proposed.text
    data = proposed.json()
    assert data["type"] == "proposal"
    assert client.get("/inventory", headers=owner).json()["items"][0]["quantity"] == 15
    done = client.post(f"/voice/proposals/{data['token']}/confirm", json={}, headers=owner)
    assert done.status_code == 200, done.text
    assert client.get("/inventory", headers=owner).json()["items"][0]["quantity"] == 19
    assert client.post(f"/voice/proposals/{data['token']}/confirm", json={}, headers=owner).status_code == 410


def test_voice_read_only_command_returns_data_without_proposal(client):
    owner, _ = new_owner(client)
    r = client.post("/voice/commands", json={"text": "read low stock"}, headers=owner)
    assert r.status_code == 200
    assert r.json()["type"] == "read_only"
    assert "No items" in r.json()["text"]


def test_voice_inventory_count_is_proposed_then_written_to_ledger(client):
    owner, _ = new_owner(client)
    client.post("/catalog", json={"name": "Roses", "kind": "ready_stock", "price_paise": 2000, "quantity": 15}, headers=owner)
    proposed = client.post("/voice/commands", json={"text": "count 12 for Roses"}, headers=owner).json()
    assert proposed["type"] == "proposal"
    assert "Set Roses stock to 12" in proposed["summary"]
    done = client.post(f"/voice/proposals/{proposed['token']}/confirm", json={}, headers=owner)
    assert done.status_code == 200, done.text
    inventory = client.get("/inventory", headers=owner).json()["items"][0]
    assert inventory["quantity"] == 12
    history = client.get(f"/inventory/{inventory['id']}/history", headers=owner).json()["history"]
    assert any(event["kind"] == "count" for event in history)


def test_voice_order_status_requires_tap_confirmation(client):
    owner, _ = new_owner(client)
    item = client.post("/catalog", json={"name": "Roses", "kind": "ready_stock", "price_paise": 2000, "quantity": 15}, headers=owner).json()
    created = client.post("/orders", headers=owner, json={"customer": {"name": "Riya"}, "items": [{"catalog_item_id": item["id"], "quantity": 1}]}).json()
    proposed = client.post("/voice/commands", json={"text": f"confirm order {created['code']}"}, headers=owner).json()
    assert proposed["type"] == "proposal"
    assert client.get(f"/orders/{created['id']}", headers=owner).json()["status"] == "new"
    assert client.post(f"/voice/proposals/{proposed['token']}/confirm", headers=owner, json={"voice_phrase": "yes"}).status_code == 403
    done = client.post(f"/voice/proposals/{proposed['token']}/confirm", headers=owner, json={})
    assert done.status_code == 200, done.text
    assert client.get(f"/orders/{created['id']}", headers=owner).json()["status"] == "confirmed"


def test_voice_proposal_is_bound_to_signed_in_user(client):
    owner, _ = new_owner(client)
    client.post("/catalog", json={"name": "Roses", "kind": "ready_stock", "price_paise": 2000, "quantity": 15}, headers=owner)
    token = client.post("/voice/commands", json={"text": "restock 4 to Roses"}, headers=owner).json()["token"]
    other, _ = new_owner(client, email="other-owner@example.com")
    assert client.post(f"/voice/proposals/{token}/confirm", json={}, headers=other).status_code == 404
    assert client.get("/inventory", headers=owner).json()["items"][0]["quantity"] == 15


def test_voice_proposal_is_bound_to_the_exact_login_session(client):
    owner, _ = new_owner(client)
    client.post("/catalog", json={"name": "Roses", "kind": "ready_stock", "price_paise": 2000, "quantity": 15}, headers=owner)
    token = client.post("/voice/commands", json={"text": "restock 4 to Roses"}, headers=owner).json()["token"]
    fresh_login = client.post("/auth/login", json={"email": "owner@example.com", "password": "correct-horse-1"}).json()
    fresh_headers = {"Authorization": f"Bearer {fresh_login['access_token']}"}
    assert client.post(f"/voice/proposals/{token}/confirm", json={}, headers=fresh_headers).status_code == 404
