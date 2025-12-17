from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.ai_provider import ConversationAIProvider
from app.audio_routing import AudioRoute, infer_audio_route_override_from_text
from app.provider_types import AIProviderId
from app.provider_selection import infer_ai_provider_override_from_text, pick_provider_for_request


class ConversationRequest(BaseModel):
    session_id: str | None = None
    user_utterance: str


class ConversationResponse(BaseModel):
    session_id: str
    reply_text: str
    timestamp_utc: datetime

    audio_route_applied: AudioRoute
    audio_cues: List[str] = Field(default_factory=list)

    ai_provider_requested: str
    ai_provider_applied: str
    ai_routing_reason: str


app = FastAPI(
    title="Halo Backend – Conversation Orchestrator",
    version="0.3.0",
    description="Conversation API with audio routing and multi-AI provider selection via voice command.",
)

provider = ConversationAIProvider()

# MVP in-memory session state
SESSION_STATE: Dict[str, Dict[str, Any]] = {}


def _state(session_id: str) -> Dict[str, Any]:
    if session_id not in SESSION_STATE:
        SESSION_STATE[session_id] = {
            "audio_route": AudioRoute.GLASSES,
            "ai_provider": None,
        }
    return SESSION_STATE[session_id]


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "halo-backend-conversation-orchestrator",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/conversation/message", response_model=ConversationResponse, tags=["conversation"])
async def handle_conversation_message(payload: ConversationRequest) -> ConversationResponse:
    session_id = payload.session_id or str(uuid4())
    st = _state(session_id)

    audio_cues: List[str] = ["session_start"]

    # Audio route override
    audio_override = infer_audio_route_override_from_text(payload.user_utterance)
    if audio_override is not None:
        st["audio_route"] = audio_override
        audio_cues.append("confirm")

    # AI provider override (voice)
    ai_override = infer_ai_provider_override_from_text(payload.user_utterance)
    if ai_override is not None:
        st["ai_provider"] = ai_override
        audio_cues.append("confirm")
        routing_reason = "explicit_override"
    else:
        routing_reason = "session_locked" if st.get("ai_provider") is not None else "default_policy"

    # Requested provider
    requested: AIProviderId = st["ai_provider"] if st.get("ai_provider") is not None else pick_provider_for_request(payload.user_utterance)

    # Persist provider chosen by default_policy so follow-ups become session_locked
    if st.get("ai_provider") is None:
        st["ai_provider"] = requested
    
    # Provider call (falls back internally if missing keys)
    result = await provider.generate_reply(
        user_utterance=payload.user_utterance,
        session_context={"session_id": session_id},
        provider_requested=requested,
    )

    return ConversationResponse(
        session_id=session_id,
        reply_text=result.reply_text,
        timestamp_utc=datetime.now(timezone.utc),
        audio_route_applied=st["audio_route"],
        audio_cues=audio_cues,
        ai_provider_requested=requested.value,
        ai_provider_applied=result.provider_applied.value,
        ai_routing_reason=f"{routing_reason}:{result.routing_note}",
    )



