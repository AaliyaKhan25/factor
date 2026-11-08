"""Gnani.ai Indic voice adapter for speech-to-text integration."""
import logging
import os
from typing import Optional
import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Gnani.ai ASR configuration defaults
GNANI_ASR_URL = os.environ.get("GNANI_ASR_URL", "https://asr.gnani.ai/v1/recognize")
GNANI_LANG_CODE = os.environ.get("GNANI_LANG_CODE", "en-IN")


def is_gnani_configured() -> bool:
    """Check if Gnani AI credentials are present."""
    return bool(
        settings.gnani_token
        or settings.gnani_api_key
        or os.environ.get("GNANI_TOKEN")
        or os.environ.get("GNANI_API_KEY")
    )


async def transcribe_with_gnani(
    audio_bytes: bytes,
    content_type: str = "audio/wav",
    language: str = "en-IN",
) -> str:
    """Send voice audio to Gnani.ai ASR API to transcribe Indic speech.
    
    Supports Indian English (en-IN), Hindi (hi-IN), Kannada (kn-IN),
    Tamil (ta-IN), Telugu (te-IN), Gujarati (gu-IN), Marathi (mr-IN), etc.
    """
    token = (
        settings.gnani_token
        or settings.gnani_api_key
        or os.environ.get("GNANI_TOKEN")
        or os.environ.get("GNANI_API_KEY")
        or ""
    )
    access_key = settings.gnani_access_key or os.environ.get("GNANI_ACCESS_KEY", "")
    url = settings.gnani_asr_url or GNANI_ASR_URL
    lang = language or settings.gnani_lang_code or GNANI_LANG_CODE

    if not token and not access_key:
        logger.warning("Gnani.ai token not configured in environment.")
        raise ValueError(
            "Gnani.ai API key/token not found. Please set GNANI_API_KEY or GNANI_TOKEN in your environment."
        )

    headers = {
        "token": token,
        "accessKey": access_key,
        "language": lang,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    files = {"file": ("voice_input.wav", audio_bytes, content_type)}
    data = {"language": lang, "encoding": "wav"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)
            if resp.status_code != 200:
                logger.error("Gnani ASR call failed: %d %s", resp.status_code, resp.text)
                raise RuntimeError(f"Gnani.ai ASR returned status {resp.status_code}: {resp.text}")

            res_json = resp.json()
            transcript = (
                res_json.get("transcript")
                or res_json.get("text")
                or (res_json.get("data") or {}).get("transcript")
                or res_json.get("result")
                or ""
            )
            return transcript.strip()
    except httpx.RequestError as exc:
        logger.error("Network error communicating with Gnani AI: %s", exc)
        raise RuntimeError(f"Network error connecting to Gnani.ai: {str(exc)}")
