"""Password hashing, JWT creation and validation, session checks."""
import base64
import hashlib
import hmac
import os
import secrets
from datetime import timedelta

import jwt

from ..config import settings
from ..utils.time import utcnow

# scrypt parameters (about 16 MB of memory per hash)
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return "scrypt${}${}".format(base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return hmac.compare_digest(actual, expected)


def create_access_token(user_id: int) -> str:
    now = utcnow()
    payload = {"sub": str(user_id), "sid": secrets.token_urlsafe(24), "iat": now, "exp": now + timedelta(minutes=settings.jwt_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> int | None:
    """Return the user id, or None if the token is invalid or expired."""
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return int(data["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def decode_access_session(token: str) -> str | None:
    """Return the signed-in session id from a valid access token."""
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return str(data["sid"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
