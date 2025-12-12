from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel


class ConversationRequest(BaseModel):
    session_id: str | None = None
    user_utterance: str


class ConversationResponse(BaseModel):
    session_id: str
    reply_text: str
    timestamp_utc: datetime


app = FastAPI(
    title="Halo Backend – Conversation Orchestrator",
    version="0.1.0",
    description=(
        "Core API for orchestrating conversational sessions between "
        "Halo clients (mobile/glasses) and downstream AI providers."
    ),
)


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

    For MVP 1.0 this implementation is intentionally minimal:
    - if session_id is not provided, a new session_id is generated;
    - the assistant reply is a stubbed echo of the user utterance.

    In future iterations this endpoint will:
    - call the AI provider(s) selected in SAD and RTM;
    - apply orchestration rules (context, safety, logging);
    - integrate with monitoring and audit logging.
    """
    session_id = payload.session_id or str(uuid4())

    # Stubbed reply for MVP skeleton
    reply_text = f"Echo: {payload.user_utterance}"

    return ConversationResponse(
        session_id=session_id,
        reply_text=reply_text,
        timestamp_utc=datetime.now(timezone.utc),
    )
