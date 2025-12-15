from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict

import httpx

from app.provider_types import AIProviderId


@dataclass(frozen=True)
class ProviderResult:
    reply_text: str
    provider_applied: AIProviderId
    routing_note: str


class ConversationAIProvider:
    async def generate_reply(
        self,
        user_utterance: str,
        session_context: Dict[str, Any],
        provider_requested: AIProviderId,
    ) -> ProviderResult:
        if provider_requested == AIProviderId.OPENAI:
            return await self._openai(user_utterance)

        if provider_requested == AIProviderId.PERPLEXITY:
            return await self._perplexity(user_utterance)

        if provider_requested == AIProviderId.CLOUD_AI:
            return await self._gemini(user_utterance)

        if provider_requested == AIProviderId.PRO_ACTOR:
            return await self._openai_compatible(
                user_utterance=user_utterance,
                base_url=os.getenv("PRO_ACTOR_BASE_URL") or "",
                api_key=os.getenv("PRO_ACTOR_API_KEY") or "",
                model=os.getenv("PRO_ACTOR_MODEL") or "default",
                provider_name=AIProviderId.PRO_ACTOR,
            )

        # Notion Calendar is handled as client action in main.py (MVP placeholder)
        if provider_requested == AIProviderId.NOTION_CALENDAR:
            return ProviderResult(
                reply_text="Notion Calendar selected (client action required).",
                provider_applied=AIProviderId.NOTION_CALENDAR,
                routing_note="notion_calendar_placeholder",
            )

        return ProviderResult(
            reply_text=f"ECHO: {user_utterance}",
            provider_applied=AIProviderId.ECHO,
            routing_note="echo_stub",
        )

    async def _openai(self, user_utterance: str) -> ProviderResult:
        key = os.getenv("OPENAI_API_KEY") or ""
        if not key:
            return ProviderResult(f"ECHO: {user_utterance}", AIProviderId.ECHO, "fallback_missing_OPENAI_API_KEY")

        model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": "halo-mvp/0.1"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": user_utterance}],
            "temperature": 0.2,
        }

        try:
            async with httpx.AsyncClient(timeout=25) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                txt = data["choices"][0]["message"]["content"]
            return ProviderResult(txt, AIProviderId.OPENAI, "openai_chat_completions")
        except Exception as e:
            return ProviderResult(f"ECHO: {user_utterance}", AIProviderId.ECHO, f"fallback_openai_error:{type(e).__name__}")

    async def _perplexity(self, user_utterance: str) -> ProviderResult:
        key = os.getenv("PERPLEXITY_API_KEY") or ""
        if not key:
            return ProviderResult(f"ECHO: {user_utterance}", AIProviderId.ECHO, "fallback_missing_PERPLEXITY_API_KEY")

        model = os.getenv("PERPLEXITY_MODEL") or "sonar"
        url = "https://api.perplexity.ai/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": "halo-mvp/0.1"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": user_utterance}],
            "temperature": 0.2,
        }

        try:
            async with httpx.AsyncClient(timeout=25) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                txt = data["choices"][0]["message"]["content"]
            return ProviderResult(txt, AIProviderId.PERPLEXITY, "perplexity_chat_completions")
        except Exception as e:
            return ProviderResult(f"ECHO: {user_utterance}", AIProviderId.ECHO, f"fallback_perplexity_error:{type(e).__name__}")

    async def _gemini(self, user_utterance: str) -> ProviderResult:
        key = os.getenv("GEMINI_API_KEY") or ""
        if not key:
            return ProviderResult(f"ECHO: {user_utterance}", AIProviderId.ECHO, "fallback_missing_GEMINI_API_KEY")

        model = os.getenv("GEMINI_MODEL") or "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": user_utterance}]}]}

        try:
            async with httpx.AsyncClient(timeout=25) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                txt = data["candidates"][0]["content"]["parts"][0]["text"]
            return ProviderResult(txt, AIProviderId.CLOUD_AI, "gemini_generateContent")
        except Exception as e:
            return ProviderResult(f"ECHO: {user_utterance}", AIProviderId.ECHO, f"fallback_gemini_error:{type(e).__name__}")

    async def _openai_compatible(
        self,
        user_utterance: str,
        base_url: str,
        api_key: str,
        model: str,
        provider_name: AIProviderId,
    ) -> ProviderResult:
        if not base_url or not api_key:
            return ProviderResult(f"ECHO: {user_utterance}", AIProviderId.ECHO, f"fallback_missing_{provider_name.value}_config")

        url = base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": user_utterance}],
            "temperature": 0.2,
        }

        try:
            async with httpx.AsyncClient(timeout=25) as client:
                r = await client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                txt = data["choices"][0]["message"]["content"]
            return ProviderResult(txt, provider_name, f"{provider_name.value}_openai_compatible")
        except Exception as e:
            return ProviderResult(f"ECHO: {user_utterance}", AIProviderId.ECHO, f"fallback_{provider_name.value}_error:{type(e).__name__}")

