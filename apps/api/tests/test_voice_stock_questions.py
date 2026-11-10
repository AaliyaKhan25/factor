"""Spoken questions and commands must work whether STT returns English, Hinglish or Devanagari."""
import pytest
from tests.conftest import new_owner
from app.ai import voice_text


def _setup(client):
    owner, _ = new_owner(client)
    client.post("/catalog", json={"name": "Roses", "kind": "ready_stock", "price_paise": 2000, "quantity": 15}, headers=owner)
    client.post("/catalog", json={"name": "Bridal Set", "kind": "ready_stock", "price_paise": 9000, "quantity": 3}, headers=owner)
    return owner


def _say(client, owner, text):
    r = client.post("/voice/commands", json={"text": text}, headers=owner)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("phrase", [
    "how many roses are left",
    "How many roses are left?",
    "हाउ मेनी रोजेस आर लेफ्ट?",
    "roses kitne bache hain",
    "rose ka stock",
    "stock of rose",
])
def test_stock_question_in_any_form(client, phrase):
    owner = _setup(client)
    data = _say(client, owner, phrase)
    assert data["type"] == "read_only", data
    assert "Roses: 15 left" in data["text"]


def test_low_stock_flags_small_items(client):
    owner = _setup(client)
    data = _say(client, owner, "which items are running low on stock")
    assert "Bridal Set" in data["text"] and "Roses" not in data["text"]


def test_restock_with_number_words_and_devanagari(client):
    owner = _setup(client)
    data = _say(client, owner, "restock four to roses")
    assert data["type"] == "proposal"
    data = _say(client, owner, "रोजेस में 10 add करो")
    assert data["type"] == "proposal"


def test_unknown_item_asks_which_one(client):
    owner = _setup(client)
    data = _say(client, owner, "how many lilies are left")
    assert data["type"] == "needs_clarification"
    assert "Roses" in data["text"]


def test_helpers():
    assert voice_text.numberize("add twenty five to roses") == "add 25 to roses"
    assert voice_text.numberize("restock char") == "restock 4"