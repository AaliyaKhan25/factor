"""Gnani.ai Indic voice adapter for speech-to-text integration."""
import logging
import os
import json
from typing import Optional
import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Gnani.ai ASR configuration defaults
GNANI_ASR_URL = os.environ.get("GNANI_ASR_URL", "https://asr.gnani.ai/v1/recognize")
GNANI_LANG_CODE = os.environ.get("GNANI_LANG_CODE", "en-IN")


def _api_key() -> str:
    """Accept both documented key names used by existing Factor deployments."""
    return (settings.gnani_api_key or settings.gnani_token or os.environ.get("GNANI_API_KEY", "")
            or os.environ.get("GNANI_TOKEN", ""))


def is_gnani_configured() -> bool:
    """Check the server-only Gnani credentials under either supported env name."""
    return bool(_api_key())


async def transcribe_with_gnani(
    audio_bytes: bytes,
    content_type: str = "audio/wav",
    language: str = "en-IN",
    key_terms: list[str] | None = None,
) -> str:
    """Send voice audio to Gnani.ai ASR API to transcribe Indic speech.
    
    Supports Indian English (en-IN), Hindi (hi-IN), Kannada (kn-IN),
    Tamil (ta-IN), Telugu (te-IN), Gujarati (gu-IN), Marathi (mr-IN), etc.
    """
    token = _api_key()
    if not token:
        raise ValueError("GNANI_API_KEY is not configured on the server")
    url = settings.gnani_stt_url
    lang = language if language not in ("", "indic-auto") else (settings.gnani_lang_code or GNANI_LANG_CODE)
    headers = {"X-API-Key-ID": token}
    files = {"audio_file": ("voice_input.wav", audio_bytes, content_type)}
    # Without a format, the model writes English words in Devanagari ("हाउ मेनी रोजेस"), which the command
    # parser cannot read. "transliterate" returns everything in Latin letters and detects the language itself.
    fmt = settings.gnani_stt_format or "transliterate"
    data = {"model": "prisma-v3.0", "format": fmt}
    data["language_code"] = lang
    data["preferred_language"] = lang
    data["itn_native_numerals"] = "true"
    if key_terms:
        data["key_terms"] = json.dumps(key_terms[:200], ensure_ascii=False)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)
            if resp.status_code != 200:
                logger.error("Gnani ASR call failed: %d %s", resp.status_code, resp.text)
                raise RuntimeError(f"Gnani.ai ASR returned status {resp.status_code}: {resp.text}")

            res_json = resp.json()
            transcript = _transcript_from(res_json)
            if not transcript:
                logger.error("Gnani ASR response had no transcript; keys=%s", list(res_json) if isinstance(res_json, dict) else type(res_json).__name__)
                raise RuntimeError("Gnani.ai returned an empty transcript. Try speaking closer to the microphone.")
            return transcript.strip()
    except httpx.RequestError as exc:
        logger.error("Network error communicating with Gnani AI: %s", exc)
        raise RuntimeError(f"Network error connecting to Gnani.ai: {str(exc)}")


def _transcript_from(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("transcript", "text", "transcription"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        for key in ("data", "result", "results", "output"):
            found = _transcript_from(value.get(key))
            if found:
                return found
    if isinstance(value, list):
        return " ".join(found for found in (_transcript_from(row) for row in value) if found)
    return ""


async def speak_with_gnani(text: str) -> bytes:
    """Request a WAV response from Gnani TTS without exposing credentials to the browser."""
    token = _api_key()
    if not token:
        raise ValueError("GNANI_API_KEY is not configured on the server")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(settings.gnani_tts_url,
            headers={"X-API-Key-ID": token, "Content-Type": "application/json"},
            json={"text": text[:1500], "voice": "Kaveri", "model": "timbre-v2.5",
                  "language": "en-IN", "speed": 1.0,
                  "audio_config": {"encoding": "linear_pcm", "container": "wav",
                                   "sample_rate": 48000, "num_channels": 1, "sample_width": 2}})
        response.raise_for_status()
        if response.headers.get("content-type", "").startswith("audio/"):
            return response.content
        data = response.json()
        encoded = data.get("audio_content") or data.get("audio_base64") or data.get("audio")
        if not encoded:
            raise RuntimeError("Gnani TTS response did not contain audio")
        import base64
        return base64.b64decode(encoded)
