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
