"""Authenticated encryption for seller courier credentials and webhook secrets."""
import os

from cryptography.fernet import Fernet

from ..config import settings


def _fernet() -> Fernet:
    key = settings.courier_encryption_key or os.environ.get("COURIER_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError("COURIER_ENCRYPTION_KEY must be configured before saving courier credentials")
    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise RuntimeError("COURIER_ENCRYPTION_KEY must be a valid Fernet key") from exc


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()
