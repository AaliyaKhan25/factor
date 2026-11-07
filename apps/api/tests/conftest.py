"""Shared test setup: an in-memory database per test and a few helpers."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.db import Base, get_db
from app.main import app

PASSWORD = "correct-horse-1"


@pytest.fixture()
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def register(client, email, name="Test User"):
    """Sign up and log in. Returns auth headers."""
    r = client.post("/auth/signup", json={"email": email, "password": PASSWORD, "name": name})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def create_business(client, headers, name="Priya Crochet"):
    r = client.post("/business", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def new_owner(client, email="owner@example.com", business="Priya Crochet"):
    """A signed-up owner with a business. Returns (headers, business_code)."""
    headers = register(client, email, name="Owner")
    return headers, create_business(client, headers, business)["business_code"]


def member_id(client, owner_headers, email):
    rows = client.get("/team/members", headers=owner_headers).json()
    return next(r["id"] for r in rows if r["email"] == email)
