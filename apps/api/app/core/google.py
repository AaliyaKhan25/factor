"""Verify a Google sign-in token. Kept separate so tests can replace it.

The google-auth package is only needed when Google sign-in is switched on, so it is imported lazily.
"""
from ..config import settings


def verify_google_token(credential: str) -> dict:
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    return id_token.verify_oauth2_token(credential, google_requests.Request(), settings.google_client_id)
