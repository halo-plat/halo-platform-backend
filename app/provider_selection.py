from __future__ import annotations

from typing import Optional
from app.provider_types import AIProviderId

def infer_ai_provider_override_from_text(user_text: str) -> Optional[AIProviderId]:
    t = (user_text or "").strip().lower()
    if not t:
        return None

    # IT + EN voice commands
    # OpenAI / ChatGPT
    if ("use chatgpt" in t) or ("use openai" in t) or ("usa chatgpt" in t) or ("usa openai" in t):
        return AIProviderId.OPENAI

    # Perplexity
    if ("use perplexity" in t) or ("usa perplexity" in t):
        return AIProviderId.PERPLEXITY

    # Cloud AI (Gemini)
    if ("use cloud ai" in t) or ("usa cloud ai" in t) or ("use gemini" in t) or ("usa gemini" in t):
        return AIProviderId.CLOUD_AI

    # Notion Calendar
    if ("use notion calendar" in t) or ("usa notion calendar" in t) or ("usa calendario notion" in t):
        return AIProviderId.NOTION_CALENDAR

    # Pro-actor AI (generic OpenAI-compatible)
    if ("use pro actor" in t) or ("use pro-actor" in t) or ("usa pro actor" in t) or ("usa pro-actor" in t):
        return AIProviderId.PRO_ACTOR

    # Explicit echo for deterministic test/dev
    if ("use echo" in t) or ("usa echo" in t):
        return AIProviderId.ECHO

    return None


def pick_default_provider_for_text(user_text: str) -> AIProviderId:
    # Routing policy: explicit_only by default (MVP control via voice command).
    # If you want lightweight auto-routing later, extend here.
    import os
    default_id = (os.getenv("HALO_AI_DEFAULT_PROVIDER") or "echo").strip().lower()

    try:
        return AIProviderId(default_id)
    except Exception:
        return AIProviderId.ECHO
