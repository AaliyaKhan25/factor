"""The whole app can be driven by speech: navigation, briefings, spoken confirmations and spoken errors."""
import pytest
from tests.conftest import new_owner


def _setup(client):
    owner, _ = new_owner(client)
    item = client.post("/catalog", json={"name": "Roses", "kind": "ready_stock", "price_paise": 2000, "quantity": 15}, headers=owner).json()
    order = client.post("/orders", headers=owner, json={"customer": {"name": "Riya"}, "items": [{"catalog_item_id": item["id"], "quantity": 1}]}).json()
    return owner, order


def _say(client, owner, text):
    r = client.post("/voice/commands", json={"text": text}, headers=owner)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("phrase,path", [
    ("open orders", "/orders"), ("go to inventory", "/inventory"), ("take me to the inbox", "/inbox"),
    ("open settings", "/settings"), ("open catalog", "/catalog"), ("go to customers", "/customers"),
    ("open the dashboard", "/dashboard"), ("open new order", "/orders/new"),
    ("ऑर्डर्स kholo", "/orders"), ("go to team", "/setup/team"), ("go back", "back"),
])
def test_navigation_phrases(client, phrase, path):
    owner, _ = _setup(client)
    data = _say(client, owner, phrase)
    assert data["type"] == "navigate" and data["path"] == path, data


def test_open_a_specific_order(client):
    owner, order = _setup(client)
    data = _say(client, owner, f"open order {order['code']}")
    assert data["type"] == "navigate" and data["path"] == f"/orders/{order['id']}"


def test_open_unknown_order_is_a_speakable_error(client):
    owner, _ = _setup(client)
    r = client.post("/voice/commands", json={"text": "open order ORD-9999"}, headers=owner)
    assert r.status_code == 404 and "ORD-9999" in r.json()["detail"]


def test_briefing_and_help_are_read_aloud(client):
    owner, _ = _setup(client)
    brief = _say(client, owner, "give me a summary")
    assert brief["type"] == "read_only" and "orders" in brief["text"]
    assert _say(client, owner, "what can I say")["intent"] == "help"


def test_spoken_yes_confirms_and_stray_words_do_not(client):
    owner, _ = _setup(client)
    token = _say(client, owner, "restock 4 to roses")["token"]
    assert client.post(f"/voice/proposals/{token}/confirm", json={"voice_phrase": "banana"}, headers=owner).status_code == 403
    ok = client.post(f"/voice/proposals/{token}/confirm", json={"voice_phrase": "haan kar do"}, headers=owner)
    assert ok.status_code == 200, ok.text
    assert client.get("/inventory", headers=owner).json()["items"][0]["quantity"] == 18


def test_spoken_no_drops_the_proposal(client):
    owner, _ = _setup(client)
    token = _say(client, owner, "restock 4 to roses")["token"]
    dropped = client.post(f"/voice/proposals/{token}/confirm", json={"voice_phrase": "no"}, headers=owner)
    assert dropped.status_code == 200 and dropped.json()["type"] == "dropped"
    assert client.get("/inventory", headers=owner).json()["items"][0]["quantity"] == 14
    assert client.post(f"/voice/proposals/{token}/confirm", json={"voice_phrase": "yes"}, headers=owner).status_code == 410


def test_cancelling_an_order_needs_the_word_cancel(client):
    owner, order = _setup(client)
    token = _say(client, owner, f"cancel order {order['code']}")["token"]
    assert client.post(f"/voice/proposals/{token}/confirm", json={"voice_phrase": "yes"}, headers=owner).status_code == 403
    ok = client.post(f"/voice/proposals/{token}/confirm", json={"voice_phrase": "yes cancel it"}, headers=owner)
    assert ok.status_code == 200, ok.text


def test_recent_orders_command_works(client):
    owner, _ = _setup(client)
    data = _say(client, owner, "show recent orders")
    assert data["type"] == "read_only" and data["items"]


def test_speak_endpoint_returns_audio_or_a_clean_503(client, monkeypatch):
    owner, _ = _setup(client)
    from app.routers import voice

    async def fake(text):
        return b"RIFFfake"
    monkeypatch.setattr(voice.speech, "speak_with_gnani", fake)
    r = client.post("/voice/speak", json={"text": "Item not found"}, headers=owner)
    assert r.status_code == 200 and r.json()["audio_base64"]

    async def boom(text):
        raise RuntimeError("no key")
    monkeypatch.setattr(voice.speech, "speak_with_gnani", boom)
    assert client.post("/voice/speak", json={"text": "x"}, headers=owner).status_code == 503