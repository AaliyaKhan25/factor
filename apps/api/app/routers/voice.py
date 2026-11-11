"""Gnani speech proxy and safe voice-command confirmation workflow."""
import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai import speech
from ..db import get_db
from ..deps import Ctx, get_ctx, require_permission
from ..models.catalog_item import CatalogItem
from ..services import voice_service

router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceCommand(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class VoiceAudio(BaseModel):
    audio_base64: str = Field(min_length=1, max_length=15_000_000)
    content_type: str = "audio/wav"
    language: str = "indic-auto"


class ConfirmProposal(BaseModel):
    voice_phrase: str | None = None


@router.get("/status")
def voice_status():
    return {"provider": "Gnani.ai", "gnani_configured": speech.is_gnani_configured(),
            "speech_to_text": True, "text_to_speech": True,
            "supported_languages": [{"code": "indic-auto", "name": "English, Hindi and Hinglish"}]}


def _command(text: str, ctx: Ctx, db: Session) -> dict:
    if not ctx.session_id:
        raise HTTPException(status_code=401, detail="Sign in again to use voice confirmations")
    return voice_service.process_command(db, ctx.business_id, ctx.user.id, ctx.session_id, text)


async def _with_speech(result: dict) -> dict:
    """Read-only answers are also spoken. Text stays usable if text to speech is unavailable."""
    if result.get("type") == "read_only":
        try:
            audio = await speech.speak_with_gnani(result["text"])
            result["audio_base64"] = base64.b64encode(audio).decode("ascii")
            result["audio_content_type"] = "audio/wav"
        except Exception:
            result["speech_available"] = False
    return result


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=600)


@router.post("/speak")
async def speak(body: SpeakIn, ctx: Ctx = Depends(get_ctx)):
    """Text to speech for prompts and errors. The browser falls back to its own voice if this fails."""
    try:
        audio = await speech.speak_with_gnani(body.text)
    except Exception:
        raise HTTPException(status_code=503, detail="Spoken replies are unavailable")
    return {"audio_base64": base64.b64encode(audio).decode("ascii"), "audio_content_type": "audio/wav"}


@router.post("/commands")
@router.post("/parse-order", include_in_schema=False)
async def voice_command(body: VoiceCommand, ctx: Ctx = Depends(require_permission("manage_orders")), db: Session = Depends(get_db)):
    return await _with_speech(_command(body.text, ctx, db))


@router.post("/transcribe-and-command")
async def transcribe_and_command(body: VoiceAudio, ctx: Ctx = Depends(require_permission("manage_orders")), db: Session = Depends(get_db)):
    try:
        audio = base64.b64decode(body.audio_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Invalid base64 audio data")
    if not audio or len(audio) > 10_000_000:
        raise HTTPException(status_code=413, detail="Audio must be between 1 byte and 10 MB")
    if not speech.is_gnani_configured():
        raise HTTPException(status_code=503, detail="Gnani voice is not configured. Set GNANI_API_KEY (or GNANI_TOKEN) in the API environment and restart the API.")
    try:
        key_terms = db.scalars(select(CatalogItem.name).where(
            CatalogItem.business_id == ctx.business_id, CatalogItem.active.is_(True)
        ).order_by(CatalogItem.id).limit(200)).all()
        transcript = await speech.transcribe_with_gnani(audio, body.content_type, body.language, list(key_terms))
        if not transcript.strip():
            raise HTTPException(status_code=422, detail="Gnani did not hear a command. Try again, or type it below.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Speech recognition failed: {exc}")
    result = await _with_speech(_command(transcript, ctx, db))
    result["transcript"] = transcript
    return result


@router.post("/proposals/{token}/confirm")
def confirm_voice_proposal(token: str, body: ConfirmProposal, ctx: Ctx = Depends(require_permission("manage_orders")), db: Session = Depends(get_db)):
    if not ctx.session_id:
        raise HTTPException(status_code=401, detail="Sign in again to confirm voice actions")
    return voice_service.confirm_proposal(db, ctx.business_id, ctx.user.id, ctx.session_id, token, voice_phrase=body.voice_phrase)


@router.post("/proposals/{token}/confirm-audio")
async def confirm_voice_proposal_by_audio(token: str, body: VoiceAudio, ctx: Ctx = Depends(require_permission("manage_orders")), db: Session = Depends(get_db)):
    if not ctx.session_id:
        raise HTTPException(status_code=401, detail="Sign in again to confirm voice actions")
    try:
        audio = base64.b64decode(body.audio_base64, validate=True)
        phrase = await speech.transcribe_with_gnani(audio, body.content_type, body.language)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not recognize confirmation: {exc}")
    return voice_service.confirm_proposal(db, ctx.business_id, ctx.user.id, ctx.session_id, token, voice_phrase=phrase)