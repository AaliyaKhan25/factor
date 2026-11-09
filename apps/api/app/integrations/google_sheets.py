"""Small Google Sheets v4 client; the service-account key stays in API env config."""
import json
from urllib.parse import quote

import httpx

from ..config import settings


class SheetsError(RuntimeError):
    pass


def _access_token() -> str:
    if not settings.google_service_account_json:
        raise SheetsError("Google service account is not configured on the server")
    try:
        info = json.loads(settings.google_service_account_json)
        from google.auth.transport.requests import Request
        from google.oauth2.service_account import Credentials

        credentials = Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        credentials.refresh(Request())
        return credentials.token
    except SheetsError:
        raise
    except Exception as exc:
        raise SheetsError(f"Could not authorize the Google service account: {exc}") from exc


def write_snapshot(spreadsheet_id: str, tabs: dict[str, list[list[str]]]) -> None:
    """Replace app-owned tabs with plain text values (RAW prevents formula evaluation)."""
    token = _access_token()
    base = f"https://sheets.googleapis.com/v4/spreadsheets/{quote(spreadsheet_id, safe='')}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=25.0) as client:
        response = client.get(base, headers=headers, params={"fields": "sheets.properties.title"})
        if response.is_error:
            raise SheetsError(f"Google Sheets could not open the shared spreadsheet ({response.status_code})")
        existing = {s["properties"]["title"] for s in response.json().get("sheets", [])}
        missing = [name for name in tabs if name not in existing]
        if missing:
            response = client.post(
                f"{base}:batchUpdate",
                headers=headers,
                json={"requests": [{"addSheet": {"properties": {"title": name}}} for name in missing]},
            )
            if response.is_error:
                raise SheetsError(f"Google Sheets could not create the sync tabs ({response.status_code})")
        for title, values in tabs.items():
            range_name = quote(f"'{title}'!A1", safe="")
            response = client.put(
                f"{base}/values/{range_name}",
                headers=headers,
                params={"valueInputOption": "RAW"},
                json={"majorDimension": "ROWS", "values": values},
            )
            if response.is_error:
                raise SheetsError(f"Google Sheets could not update the {title} tab ({response.status_code})")
