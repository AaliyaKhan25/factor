"""Signup creates a plain account; roles are never self-assigned."""
import re

from tests.conftest import PASSWORD, create_business, register


def test_signup_gives_an_account_with_no_business_and_no_access(client):
    headers = register(client, "a@example.com")
    assert client.get("/auth/me", headers=headers).json()["memberships"] == []
    assert client.get("/business", headers=headers).status_code == 403


def test_signup_cannot_choose_a_role(client):
    r = client.post(
        "/auth/signup",
        json={"email": "x@example.com", "password": PASSWORD, "name": "X", "role": "admin"},
    )
    assert r.status_code == 422


def test_duplicate_email_is_rejected_case_insensitively(client):
    register(client, "a@example.com")
    r = client.post("/auth/signup", json={"email": "A@Example.com", "password": PASSWORD, "name": "A"})
    assert r.status_code == 409


def test_short_password_is_rejected(client):
    r = client.post("/auth/signup", json={"email": "a@example.com", "password": "short", "name": "A"})
    assert r.status_code == 422


def test_wrong_password_is_rejected(client):
    register(client, "a@example.com")
    r = client.post("/auth/login", json={"email": "a@example.com", "password": "not-the-password"})
    assert r.status_code == 401


def test_requests_without_a_token_are_rejected(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_creating_a_business_makes_you_its_owner(client):
    headers = register(client, "owner@example.com")
    business = create_business(client, headers)
    assert re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}", business["business_code"])
    me = client.get("/auth/me", headers=headers).json()
    assert me["memberships"] == [{"business_id": business["id"], "role": "admin", "status": "active"}]
    details = client.get("/business", headers=headers).json()
    assert details["business_code"] == business["business_code"]
    assert "manage_team" in details["your_permissions"]


def test_an_active_member_cannot_start_a_second_business(client):
    headers = register(client, "owner@example.com")
    create_business(client, headers)
    r = client.post("/business", json={"name": "Another"}, headers=headers)
    assert r.status_code == 409
