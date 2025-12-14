from __future__ import annotations

from typing import Optional
from app.provider_types import AIProviderId

def infer_ai_provider_override_from_text(user_text: str) -> Optional[AIProviderId]:
    t = (user_text or "").strip().lower()
    if not t:
        return None

    if ("use chatgpt" in t) or ("use openai" in t) or ("usa chatgpt" in t) or ("usa openai" in t):
        return AIProviderId.OPENAI
    if ("use perplexity" in t) or ("usa perplexity" in t):
        return AIProviderId.PERPLEXITY
    if ("use cloud ai" in t) or ("usa cloud ai" in t) or ("use gemini" in t) or ("usa gemini" in t):
        return AIProviderId.CLOUD_AI
    if ("use notion calendar" in t) or ("usa notion calendar" in t) or ("usa calendario notion" in t):
        return AIProviderId.NOTION_CALENDAR
    if ("use pro actor" in t) or ("use pro-actor" in t) or ("usa pro actor" in t) or ("usa pro-actor" in t):
        return AIProviderId.PRO_ACTOR
    if ("use echo" in t) or ("usa echo" in t):
        return AIProviderId.ECHO

    return None


def pick_default_provider() -> AIProviderId:
    import os
    v = (os.getenv("HALO_AI_DEFAULT_PROVIDER") or "echo").strip().lower()
    try:
        return AIProviderId(v)
    except Exception:
        return AIProviderId.ECHO
