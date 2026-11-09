"""Google Sheets sync writes app snapshots using literal RAW values only."""
from tests.conftest import new_owner


def test_sheet_link_validation_and_raw_snapshot_tabs(client, monkeypatch):
    owner, _ = new_owner(client)
    assert client.put("/sheets", headers=owner, json={"spreadsheet_url": "not a spreadsheet"}).status_code == 422
    link = "https://docs.google.com/spreadsheets/d/abc_def-123/edit#gid=0"
    connected = client.put("/sheets", headers=owner, json={"spreadsheet_url": link})
    assert connected.status_code == 200 and connected.json()["connected"] is True
    item = client.post("/catalog", headers=owner, json={"name": "Safe", "kind": "ready_stock", "price_paise": 1000, "quantity": 2}).json()
    order = client.post("/orders", headers=owner, json={"customer": {"name": "=IMPORTXML(\"https://bad\")"},
        "items": [{"catalog_item_id": item["id"], "quantity": 1}]}).json()
    captured = {}
    monkeypatch.setattr("app.services.sheet_sync_service.google_sheets.write_snapshot",
                        lambda spreadsheet_id, tabs: captured.update(id=spreadsheet_id, tabs=tabs))
    synced = client.post("/sheets/sync-now", headers=owner)
    assert synced.status_code == 200 and synced.json()["ok"] is True
    assert captured["id"] == "abc_def-123"
    assert set(captured["tabs"]) == {"Orders", "Inventory", "Stock log"}
    assert captured["tabs"]["Orders"][1][2] == '=IMPORTXML("https://bad")'
    assert all(isinstance(value, str) for row in captured["tabs"]["Orders"] for value in row)
    assert client.get(f"/orders/{order['id']}", headers=owner).status_code == 200
