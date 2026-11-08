"""Google sign-in creates a plain account and never grants a role."""
from dataclasses import replace

from app.config import settings
from app.core import google as google_auth
from app.routers import auth as auth_router


def enable(monkeypatch, claims):
    monkeypatch.setattr(auth_router, "settings", replace(settings, google_client_id="client-id"))
    monkeypatch.setattr(google_auth, "verify_google_token", lambda cred: claims)


def test_not_configured_says_so(client):
    r = client.post("/auth/google", json={"credential": "x" * 20})
    assert r.status_code == 503
    assert client.get("/auth/config").json() == {"google_client_id": None}


def test_first_google_sign_in_creates_a_plain_account(client, monkeypatch):
    enable(monkeypatch, {"email": "Asha@Example.com", "email_verified": True, "name": "Asha Rao"})
    r = client.post("/auth/google", json={"credential": "x" * 20})
    assert r.status_code == 200
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["email"] == "asha@example.com" and me["name"] == "Asha Rao" and me["memberships"] == []
    again = client.post("/auth/google", json={"credential": "x" * 20})
    me2 = client.get("/auth/me", headers={"Authorization": f"Bearer {again.json()['access_token']}"}).json()
    assert me2["id"] == me["id"]


def test_unverified_email_and_bad_token_are_refused(client, monkeypatch):
    enable(monkeypatch, {"email": "a@example.com", "email_verified": False})
    assert client.post("/auth/google", json={"credential": "x" * 20}).status_code == 401

    def boom(cred):
        raise ValueError("bad token")

    monkeypatch.setattr(google_auth, "verify_google_token", boom)
    assert client.post("/auth/google", json={"credential": "x" * 20}).status_code == 401
