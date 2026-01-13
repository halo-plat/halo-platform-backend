from __future__ import annotations

import re
from typing import Optional

from app.provider_types import AIProviderId


# STT-hardening strategy:
# - normalize text (lower, strip, collapse spaces, remove punctuation)
# - accept multiple "switch" intents (use/usa/switch/passa/imposta/attiva)
# - match provider via token sets + common mis-hearings/aliases
#
# NOTE: We keep it deterministic and offline (no extra dependencies).


_INTENT_TOKENS = {
    "use", "usa", "switch", "passa", "imposta", "attiva", "seleziona", "set", "select"
}


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    if not s:
        return ""
    # Replace punctuation with spaces, keep letters/numbers
    s = re.sub(r"[^a-z0-9àèéìòù]+", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokens(s: str) -> set[str]:
    return set(_norm(s).split())


def _has_intent(toks: set[str]) -> bool:
    return len(toks.intersection(_INTENT_TOKENS)) > 0


def infer_ai_provider_override_from_text(user_text: str) -> Optional[AIProviderId]:
    raw = user_text or ""
    t = _norm(raw)
    if not t:
        return None

    toks = _tokens(t)

    # If there is no explicit intent token, don't accidentally switch provider
    # (avoids false positives on random phrases).
    if not _has_intent(toks):
        return None

    # Provider alias definitions (token-based)
    # We intentionally allow both EN/IT variants and common short forms.
    alias_map: list[tuple[AIProviderId, list[set[str]]]] = [
        (AIProviderId.OPENAI, [
            {"chatgpt"},
            {"openai"},
            {"gpt"},
        ]),
        (AIProviderId.PERPLEXITY, [
            {"perplexity"},
            {"pplx"},
        ]),
                (AIProviderId.CLAUDE, [
            {"claude"},
            {"anthropic"},
        ]),
        (AIProviderId.HUGGINGFACE, [
            {"hugging", "face"},
            {"huggingface"},
            {"hf"},
        ]),
(AIProviderId.CLOUD_AI, [
            {"cloud", "ai"},
            {"gemini"},
            {"google", "ai"},
        ]),
        (AIProviderId.NOTION_CALENDAR, [
            {"notion", "calendar"},
            {"notion"},
            {"calendario", "notion"},
        ]),
        (AIProviderId.PRO_ACTOR, [
            {"pro", "actor"},
            {"proactor"},
            {"pro", "attore"},  # occasional IT STT
        ]),
        (AIProviderId.ECHO, [
            {"echo"},
            {"eco"},  # IT STT common for "echo"
        ]),
    ]

    for provider_id, alias_sets in alias_map:
        for aset in alias_sets:
            if aset.issubset(toks):
                return provider_id

    return None


def pick_default_provider() -> AIProviderId:
    import os
    v = (os.getenv("HALO_AI_DEFAULT_PROVIDER") or "echo").strip().lower()
    try:
        return AIProviderId(v)
    except Exception:
        return AIProviderId.ECHO

# --- Auto-routing policy (MVP) ---
def _env_truthy(name: str) -> bool:
    import os
    v = (os.getenv(name) or "").strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def pick_provider_for_request(user_text: str) -> AIProviderId:
    """
    Policy-based provider selection when there is NO explicit voice override.
    Enable with HALO_AI_AUTO_ROUTING=1.
    """
    default_provider = pick_default_provider()

    if not _env_truthy("HALO_AI_AUTO_ROUTING"):
        return default_provider

    t = (user_text or "").strip().lower()

    # Calendar / scheduling intent -> Notion Calendar (placeholder)
    cal_tokens = (
        "calendario", "agenda", "appuntamento", "riunione", "meeting",
        "notion calendar", "notion calendario", "invito", "invita", "schedule",
    )
    if any(tok in t for tok in cal_tokens):
        return AIProviderId.NOTION_CALENDAR

    # OS / tool action intent -> Pro Actor (placeholder)
    action_tokens = (
        "trova file", "cerca file", "localizza file", "apri file", "invia file",
        "manda file", "carica file", "upload", "download", "salva", "sposta file",
        "open file", "find file", "send file",
    )
    if any(tok in t for tok in action_tokens):
        return AIProviderId.PRO_ACTOR

    # Web/search/news intent -> Perplexity
    search_tokens = (
        "news", "notizie", "oggi", "ieri", "ultima", "ultime", "latest", "recent",
        "prezzo", "quanto costa", "costi", "media", "con fonti", "fonti", "citazioni",
        "sources", "cita le fonti", "cerca", "ricerca", "search", "web",
    )
    if any(tok in t for tok in search_tokens):
        return AIProviderId.PERPLEXITY

    # Claude and Hugging Face are explicit-override providers in MVP;
    # no implicit auto-routing to avoid unexpected cost/latency shifts.


    return default_provider
