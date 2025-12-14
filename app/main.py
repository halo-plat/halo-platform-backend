from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.ai_provider import ConversationAIProvider
from app.audio_routing import AudioRoute, infer_audio_route_override_from_text
from app.provider_types import AIProviderId
from app.provider_selection import infer_ai_provider_override_from_text, pick_default_provider_for_text
from app.notion_calendar import build_notion_calendar_show_event_url, build_demo_event


class ConversationRequest(BaseModel):
    session_id: str | None = None
    user_utterance: str


class ClientAction(BaseModel):
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    session_id: str
    reply_text: str
    timestamp_utc: datetime

    # EarPhones routing/cues (already in MVP path)
    audio_route_applied: AudioRoute
    audio_cues: List[str] = Field(default_factory=list)

    # Multi-AI routing (new)
    ai_provider_requested: AIProviderId
    ai_provider_applied: AIProviderId
    ai_routing_reason: str

    # Optional client actions (e.g., Notion Calendar deep link)
    client_actions: List[ClientAction] = Field(default_factory=list)


app = FastAPI(
    title="Halo Backend – Conversation Orchestrator",
    version="0.3.0",
    description="Core API for orchestrating conversational sessions and routing to downstream AI providers.",
)

provider = ConversationAIProvider()

# Minimal in-memory session state (MVP): {session_id: {audio_route, ai_provider}}
SESSION_STATE: Dict[str, Dict[str, Any]] = {}


def _state(session_id: str) -> Dict[str, Any]:
    if session_id not in SESSION_STATE:
        SESSION_STATE[session_id] = {
            "audio_route": AudioRoute.GLASSES,
            "ai_provider": None,  # force explicit voice selection unless default is set
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
    ai_routing_reason = "policy_default"

    # 1) Audio route override (EarPhones)
    audio_override = infer_audio_route_override_from_text(payload.user_utterance)
    if audio_override is not None:
        st["audio_route"] = audio_override
        audio_cues.append("confirm")

    # 2) AI provider override (voice command)
    ai_override = infer_ai_provider_override_from_text(payload.user_utterance)
    if ai_override is not None:
        st["ai_provider"] = ai_override
        ai_routing_reason = "explicit_override"
        audio_cues.append("confirm")

    # 3) Requested provider resolution (explicit session setting OR configured default)
    requested: AIProviderId
    if st.get("ai_provider") is not None:
        requested = st["ai_provider"]
        if ai_routing_reason != "explicit_override":
            ai_routing_reason = "session_locked"
    else:
        requested = pick_default_provider_for_text(payload.user_utterance)

    client_actions: List[ClientAction] = []

    # 4) Notion Calendar local action (cron:// deep link)
    if requested == AIProviderId.NOTION_CALENDAR:
        demo = build_demo_event(session_id=session_id)
        account_email = (payload.user_utterance or "").strip()
        if "@" not in account_email:
            account_email = os.getenv("NOTION_CALENDAR_ACCOUNT_EMAIL") or ""
        if not account_email:
            reply_text = "Notion Calendar selected. Set NOTION_CALENDAR_ACCOUNT_EMAIL or say your account email."
            applied = AIProviderId.NOTION_CALENDAR
            return ConversationResponse(
                session_id=session_id,
                reply_text=reply_text,
                timestamp_utc=datetime.now(timezone.utc),
                audio_route_applied=st["audio_route"],
                audio_cues=audio_cues,
                ai_provider_requested=requested,
                ai_provider_applied=applied,
                ai_routing_reason=ai_routing_reason,
                client_actions=[],
            )

        url = build_notion_calendar_show_event_url(
            account_email=account_email,
            ical_uid=demo["ical_uid"],
            start_utc=demo["start_utc"],
            end_utc=demo["end_utc"],
            title=demo["title"],
        )
        client_actions.append(ClientAction(type="open_url", payload={"url": url}))
        reply_text = "Notion Calendar action emitted to client."
        applied = AIProviderId.NOTION_CALENDAR

        return ConversationResponse(
            session_id=session_id,
            reply_text=reply_text,
            timestamp_utc=datetime.now(timezone.utc),
            audio_route_applied=st["audio_route"],
            audio_cues=audio_cues,
            ai_provider_requested=requested,
            ai_provider_applied=applied,
            ai_routing_reason=ai_routing_reason,
            client_actions=client_actions,
        )

    # 5) LLM provider call (OpenAI / Perplexity / Gemini / Pro-actor / Echo fallback)
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
        ai_provider_requested=requested,
        ai_provider_applied=result.provider_applied,
        ai_routing_reason=f"{ai_routing_reason}:{result.routing_note}",
        client_actions=client_actions,
    )
