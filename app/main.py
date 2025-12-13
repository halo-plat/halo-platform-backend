from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict

from fastapi import FastAPI
from pydantic import BaseModel

from app.ai_provider import ConversationAIProvider
from app.audio_routing import AudioRoute, infer_audio_route_override_from_text


class ConversationRequest(BaseModel):
    session_id: str | None = None
    user_utterance: str
    audio_route_request: AudioRoute | None = None  # MVP hint (client preference/policy)


class ConversationResponse(BaseModel):
    session_id: str
    reply_text: str
    timestamp_utc: datetime
    audio_route_applied: AudioRoute
    audio_cues: list[str]


app = FastAPI(
    title="Halo Backend – Conversation Orchestrator",
    version="0.2.0",
    description=(
        "Core API for orchestrating conversational sessions between "
        "Halo clients (mobile/glasses) and downstream AI providers."
    ),
)

# For MVP 1.0 a single global provider instance is sufficient.
provider = ConversationAIProvider()

# Session-scoped routing state (MVP). Later: persist in a session/context service.
_SESSION_AUDIO_ROUTE: Dict[str, AudioRoute] = {}


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """
    Minimal health endpoint used by infrastructure and monitoring.
    """
    return {
        "status": "ok",
        "service": "halo-backend-conversation-orchestrator",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.post(
    "/api/v1/conversation/message",
    response_model=ConversationResponse,
    tags=["conversation"],
)
async def handle_conversation_message(payload: ConversationRequest) -> ConversationResponse:
    """
    Handle a single user utterance within a conversational session.

    The orchestration responsibilities are:
    - manage the session identifier;
    - delegate reply generation to the AI provider abstraction;
    - enforce a consistent response schema for downstream clients;
    - provide an audio routing decision hint for clients (EarPhones integration, MVP).
    """
    session_id = payload.session_id or str(uuid4())

    # EarPhones integration: allow in-session override via utterance, else accept client request,
    # else retain last route, else default to glasses.
    cues: list[str] = ["session_start"]

    override = infer_audio_route_override_from_text(payload.user_utterance)
    if override is not None:
        _SESSION_AUDIO_ROUTE[session_id] = override
        cues.append("confirm")
    elif payload.audio_route_request is not None:
        _SESSION_AUDIO_ROUTE[session_id] = payload.audio_route_request
        cues.append("confirm")

    audio_route_applied = _SESSION_AUDIO_ROUTE.get(session_id, AudioRoute.GLASSES)

    reply_text = await provider.generate_reply(
        user_utterance=payload.user_utterance,
        session_context={"session_id": session_id, "audio_route": audio_route_applied.value},
    )

    return ConversationResponse(
        session_id=session_id,
        reply_text=reply_text,
        timestamp_utc=datetime.now(timezone.utc),
        audio_route_applied=audio_route_applied,
        audio_cues=cues,
    )
