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
    assert any(l["code"] == "en-IN" for l in data["supported_languages"])
    assert any(l["code"] == "hi-IN" for l in data["supported_languages"])


def test_voice_order_auto_creation_endpoint(client):
    owner, _ = new_owner(client)

    # Post exact user prompt voice command
    payload = {
        "text": "rahul bought 80 roses , total price 1600",
        "language": "en-IN",
    }
    r = client.post("/voice/parse-order", json=payload, headers=owner)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["success"] is True
    assert data["provider"] == "Gnani.ai"
    assert data["transcript"] == "rahul bought 80 roses , total price 1600"
    assert data["order"]["customer_name"] == "Rahul"
    assert data["order"]["total_paise"] == 160000

    order_id = data["order"]["id"]

    # Verify the order exists in the orders endpoint
    order_detail = client.get(f"/orders/{order_id}", headers=owner).json()
    assert order_detail["customer"]["name"] == "Rahul"
    assert order_detail["source"] == "voice"
    assert order_detail["total_paise"] == 160000
    assert len(order_detail["items"]) == 1
    assert order_detail["items"][0]["name"] == "Roses"
    assert order_detail["items"][0]["quantity"] == 80
