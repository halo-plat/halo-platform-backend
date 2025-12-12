from dataclasses import dataclass
from enum import Enum
from typing import Any


class ProviderType(str, Enum):
    ECHO = "echo"
    # In future iterations:
    # OPENAI = "openai"
    # AZURE_OPENAI = "azure_openai"
    # CUSTOM = "custom"


@dataclass
class ProviderConfig:
    provider_type: ProviderType = ProviderType.ECHO
    # Placeholder for future configuration:
    # api_key: str | None = None
    # endpoint_url: str | None = None
    # model_name: str | None = None


class ConversationAIProvider:
    """
    Thin abstraction around the underlying AI provider(s).

    For MVP 1.0 this implementation is intentionally minimal
    and uses a stubbed echo provider.
    """

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self.config = config or ProviderConfig()

    async def generate_reply(self, user_utterance: str, session_context: dict[str, Any] | None = None) -> str:
        """
        Generate an assistant reply for a given user utterance.

        In future iterations this method will:
        - call the configured LLM / AI provider;
        - apply safety and orchestration rules;
        - log relevant metadata for audit and monitoring.
        """
        if self.config.provider_type == ProviderType.ECHO:
            return f"Echo: {user_utterance}"

        # Fallback – should not happen with current config
        return f"[unconfigured-provider] {user_utterance}"
