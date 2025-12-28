from __future__ import annotations
import os
import threading

from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Dict, List

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.ai_provider import ConversationAIProvider
from app.audio_routing import AudioRoute, infer_audio_route_override_from_text
from app.provider_types import AIProviderId
from app.provider_selection import infer_ai_provider_override_from_text, pick_provider_for_request


class ConversationRequest(BaseModel):
    session_id: str | None = None
    user_utterance: str
    audio_route_request: AudioRoute | None = None  # MVP hint (client preference/policy)


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


TENANTS_SEEN: set[str] = set()
TENANTS_LOCK = threading.Lock()


def _max_tenants_from_env() -> int:
    raw = (os.getenv("HALO_MAX_TENANTS") or "128").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 128
    return max(0, n)


def _enforce_distinct_tenant_cap(tenant_id: str) -> None:
    max_tenants = _max_tenants_from_env()
    if max_tenants == 0:
        return

    with TENANTS_LOCK:
        if tenant_id not in TENANTS_SEEN:
            if len(TENANTS_SEEN) >= max_tenants:
                raise HTTPException(status_code=429, detail="Tenant capacity exceeded")
            TENANTS_SEEN.add(tenant_id)




TENANTS_SEEN: set[str] = set()

def _max_tenants() -> int:
    """Maximum number of distinct tenants (clients) supported by this server instance.
    Configurable via HALO_MAX_TENANTS (default 128).
    """
    try:
        return int((os.getenv("HALO_MAX_TENANTS") or "128").strip())
    except Exception:
        return 128
def _normalize_tenant_id(x_client_id: str | None) -> str:
    """
    Tenant identifier for multi-client MVP.
    Backward compatible: if header is missing, fall back to 'default'.
    """
    tid = (x_client_id or "default").strip()
    return tid if tid else "default"

def _state(tenant_id: str, session_id: str) -> Dict[str, Any]:
    key = f"{tenant_id}:{session_id}"
    if key not in SESSION_STATE:
        SESSION_STATE[key] = {
            "audio_route": AudioRoute.GLASSES,
            "ai_provider": None,
        }
    return SESSION_STATE[key]


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "halo-backend-conversation-orchestrator",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/conversation/message", response_model=ConversationResponse, tags=["conversation"])
async def handle_conversation_message(
    payload: ConversationRequest,
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
) -> ConversationResponse:
    session_id = payload.session_id or str(uuid4())
    tenant_id = _normalize_tenant_id(x_client_id)
    _enforce_distinct_tenant_cap(tenant_id)
    # Tenant capacity guardrail (MVP multi-client)
    if tenant_id not in TENANTS_SEEN:
        max_tenants = _max_tenants()
        if max_tenants > 0 and len(TENANTS_SEEN) >= max_tenants:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "tenant_limit_exceeded",
                    "message": f"Tenant capacity exceeded (max={max_tenants}).",
                    "tenant_id": tenant_id,
                },
            )
        TENANTS_SEEN.add(tenant_id)
    st = _state(tenant_id, session_id)
    audio_cues: List[str] = ["session_start"]

    # Audio route override
    audio_override = infer_audio_route_override_from_text(payload.user_utterance)
    if audio_override is not None:
        st["audio_route"] = audio_override
        audio_cues.append("confirm")

    elif payload.audio_route_request is not None:
        st["audio_route"] = payload.audio_route_request
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
        session_context={"session_id": session_id, "tenant_id": tenant_id},
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



