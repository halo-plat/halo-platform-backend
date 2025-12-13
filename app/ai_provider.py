from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ConversationAIProvider:
    """
    MVP provider abstraction.
    Current behavior: ECHO stub (returns the utterance).
    Future: replace with real LLM provider integration.
    """

    async def generate_reply(self, *, user_utterance: str, session_context: Dict[str, Any]) -> str:
        return f"ECHO: {user_utterance}"
