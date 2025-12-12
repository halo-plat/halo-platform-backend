from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel

from app.ai_provider import ConversationAIProvider


class ConversationRequest(BaseModel):
    session_id: str | None = None
    user_utterance: str


class ConversationResponse(BaseModel):
    session_id: str
    reply_text: str
    timestamp_utc: datetime


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
    - enforce a consistent response schema for downstream clients.
    """
    session_id = payload.session_id or str(uuid4())

    reply_text = await provider.generate_reply(
        user_utterance=payload.user_utterance,
        session_context={"session_id": session_id},
    )

    return ConversationResponse(
        session_id=session_id,
        reply_text=reply_text,
        timestamp_utc=datetime.now(timezone.utc),
    )
