"""Voice endpoints powered by Gnani.ai Indic conversational AI."""
import base64
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..ai import speech
from ..db import get_db
from ..deps import Ctx, require_permission
from ..services import voice_service

router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceOrderRequest(BaseModel):
    text: str
    language: Optional[str] = "en-IN"


class VoiceAudioRequest(BaseModel):
    audio_base64: str
    content_type: Optional[str] = "audio/wav"
    language: Optional[str] = "en-IN"


@router.get("/status")
def voice_status():
    """Return Gnani AI service status and supported languages."""
    return {
        "provider": "Gnani.ai",
        "gnani_configured": speech.is_gnani_configured(),
        "supported_languages": [
            {"code": "en-IN", "name": "Indian English"},
            {"code": "hi-IN", "name": "Hindi (हिंदी)"},
            {"code": "kn-IN", "name": "Kannada (ಕನ್ನಡ)"},
            {"code": "ta-IN", "name": "Tamil (தமிழ்)"},
            {"code": "te-IN", "name": "Telugu (తెలుగు)"},
            {"code": "gu-IN", "name": "Gujarati (ગુજરાતી)"},
            {"code": "mr-IN", "name": "Marathi (मराठी)"},
            {"code": "bn-IN", "name": "Bengali (বাংলা)"},
        ],
    }


@router.post("/parse-order")
def parse_voice_order_text(
    body: VoiceOrderRequest,
    ctx: Ctx = Depends(require_permission("manage_orders")),
    db: Session = Depends(get_db),
):
    """Parse spoken text transcribed via Gnani.ai and auto-create order."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Voice text cannot be empty")
    try:
        return voice_service.process_voice_order(
            db=db,
            business_id=ctx.business_id,
            actor_id=ctx.user.id,
            transcript=body.text,
            language=body.language or "en-IN",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/transcribe-and-order")
async def transcribe_audio_and_create_order(
    body: VoiceAudioRequest,
    ctx: Ctx = Depends(require_permission("manage_orders")),
    db: Session = Depends(get_db),
):
    """Accept base64 audio, transcribe via Gnani.ai Indic ASR, and auto-create order."""
    try:
        audio_bytes = base64.b64decode(body.audio_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 audio data")

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    try:
        transcript = await speech.transcribe_with_gnani(
            audio_bytes=audio_bytes,
            content_type=body.content_type or "audio/wav",
            language=body.language or "en-IN",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gnani.ai speech recognition failed: {str(exc)}")

    try:
        return voice_service.process_voice_order(
            db=db,
            business_id=ctx.business_id,
            actor_id=ctx.user.id,
            transcript=transcript,
            language=body.language or "en-IN",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
