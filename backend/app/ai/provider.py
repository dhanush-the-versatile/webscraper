"""LLM provider abstraction.

A thin, provider-agnostic interface over OpenAI and Anthropic chat models used
for structured (JSON) completions. Selection order under ``LLM_PROVIDER=auto``:

    OpenAI (if key) → Anthropic (if key) → None (heuristic-only mode)

Every caller must handle a ``None`` client / failed completion by falling back
to the deterministic heuristics — the platform never hard-depends on an LLM.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ai.provider")

_JSON_BLOCK_RE = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)


def extract_json(text: str) -> Any | None:
    """Leniently pull the first JSON object/array out of an LLM response."""
    if not text:
        return None
    # strip markdown fences if present
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    if match := _JSON_BLOCK_RE.search(cleaned):
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


class LLMProvider(ABC):
    """Async JSON-completion interface implemented per vendor."""

    name: str = "base"

    @abstractmethod
    async def acomplete_json(
        self, *, system: str, user: str, max_tokens: int = 4096
    ) -> Any | None:
        """Return parsed JSON from the model, or ``None`` on any failure."""


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL

    async def acomplete_json(
        self, *, system: str, user: str, max_tokens: int = 4096
    ) -> Any | None:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return extract_json(response.choices[0].message.content or "")
        except Exception as exc:  # any provider failure degrades to heuristics
            logger.warning("openai_completion_failed", error=str(exc))
            return None


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.ANTHROPIC_MODEL

    async def acomplete_json(
        self, *, system: str, user: str, max_tokens: int = 4096
    ) -> Any | None:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=f"{system}\n\nRespond with valid JSON only — no prose, no markdown fences.",
                messages=[{"role": "user", "content": user}],
            )
            if response.stop_reason == "refusal":  # safety classifiers may decline
                logger.warning("anthropic_refusal")
                return None
            text = next((b.text for b in response.content if b.type == "text"), "")
            return extract_json(text)
        except Exception as exc:
            logger.warning("anthropic_completion_failed", error=str(exc))
            return None


_provider_singleton: LLMProvider | None = None
_provider_resolved = False


def get_llm_provider() -> LLMProvider | None:
    """Return the configured provider, or ``None`` for heuristic-only mode."""
    global _provider_singleton, _provider_resolved
    if _provider_resolved:
        return _provider_singleton

    choice = settings.LLM_PROVIDER
    provider: LLMProvider | None = None
    try:
        if choice == "openai" or (choice == "auto" and settings.OPENAI_API_KEY):
            provider = OpenAIProvider()
        elif choice == "anthropic" or (choice == "auto" and settings.ANTHROPIC_API_KEY):
            provider = AnthropicProvider()
    except Exception as exc:  # SDK missing/misconfigured → heuristic mode
        logger.warning("llm_provider_init_failed", provider=choice, error=str(exc))
        provider = None

    if provider is None:
        logger.info("llm_provider_heuristic_mode")
    else:
        logger.info("llm_provider_ready", provider=provider.name)

    _provider_singleton = provider
    _provider_resolved = True
    return provider


def reset_provider_cache() -> None:
    """Testing hook: force provider re-resolution."""
    global _provider_singleton, _provider_resolved
    _provider_singleton = None
    _provider_resolved = False
