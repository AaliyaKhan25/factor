"""Connecting channels and receiving Meta webhooks."""
import hashlib
import hmac
import json

from dataclasses import replace

from app.config import settings
from app.routers import channels as channels_router
from tests.conftest import new_owner, register
from tests.test_catalog_pricing import make_item


def connect(client, owner, channel="instagram"):
    r = client.post("/channels", json={"channel": channel, "label": "shop"}, headers=owner)
    assert r.status_code == 201
    return r.json()


IG = {"object": "instagram", "entry": [{"id": "1", "messaging": [{"sender": {"id": "99887766"}, "message": {"text": "price of tote?"}}]}]}
WA = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {
    "contacts": [{"wa_id": "919000000009", "profile": {"name": "Meera"}}],
    "messages": [{"from": "919000000009", "type": "text", "text": {"body": "price of tote?"}}]}}]}]}


def test_meta_verification_handshake(client):
    owner, _ = new_owner(client)
    ch = connect(client, owner)
    ok = client.get(ch["webhook_path"], params={"hub.mode": "subscribe", "hub.verify_token": ch["verify_token"], "hub.challenge": "12345"})
    assert ok.status_code == 200 and ok.text == "12345"
    bad = client.get(ch["webhook_path"], params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "1"})
    assert bad.status_code == 403


def test_instagram_message_lands_in_the_right_business(client):
    owner_a, _ = new_owner(client, "a@example.com", "Shop A")
    owner_b, _ = new_owner(client, "b@example.com", "Shop B")
    make_item(client, owner_a, name="Sage green tote")
    ch = connect(client, owner_a)
    assert client.post(ch["webhook_path"], json=IG).json() == {"received": 1}
    convs = client.get("/inbox/conversations", headers=owner_a).json()
    assert len(convs) == 1 and convs[0]["channel"] == "instagram" and convs[0]["status"] == "agent"
    assert client.get("/inbox/conversations", headers=owner_b).json() == []


def test_whatsapp_message_gets_a_name_and_a_quote(client):
    owner, _ = new_owner(client)
    make_item(client, owner, name="Sage green tote")
    ch = connect(client, owner, "whatsapp")
    client.post(ch["webhook_path"], json=WA)
    conv = client.get("/inbox/conversations", headers=owner).json()[0]
    assert conv["display_name"] == "Meera"
    detail = client.get(f"/inbox/conversations/{conv['id']}", headers=owner).json()
    assert "Rs 850" in detail["messages"][-1]["text"]


def test_unknown_token_is_rejected(client):
    assert client.post("/webhooks/meta/not-a-real-token", json=IG).status_code == 404


def test_signature_is_checked_when_an_app_secret_is_set(client, monkeypatch):
    monkeypatch.setattr(channels_router, "settings", replace(settings, meta_app_secret="topsecret"))
    owner, _ = new_owner(client)
    ch = connect(client, owner)
    raw = json.dumps(IG).encode()
    good = "sha256=" + hmac.new(b"topsecret", raw, hashlib.sha256).hexdigest()
    headers = {"Content-Type": "application/json"}
    assert client.post(ch["webhook_path"], content=raw, headers={**headers, "X-Hub-Signature-256": "sha256=bad"}).status_code == 403
    assert client.post(ch["webhook_path"], content=raw, headers=headers).status_code == 403
    assert client.post(ch["webhook_path"], content=raw, headers={**headers, "X-Hub-Signature-256": good}).status_code == 200


def test_only_the_owner_manages_channels(client):
    owner, code = new_owner(client)
    other = register(client, "x@example.com")
    assert client.post("/channels", json={"channel": "instagram"}, headers=other).status_code == 403
    ch = connect(client, owner)
    owner_b, _ = new_owner(client, "b@example.com", "Shop B")
    assert client.delete(f"/channels/{ch['id']}", headers=owner_b).status_code == 404
