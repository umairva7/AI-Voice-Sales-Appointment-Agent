"""
Abstract base class for all LLM providers.
==========================================
Every provider implements this interface.
The /chat endpoint only ever talks to this interface — it never
knows (or cares) whether Gemini, GPT, Groq, or a toaster is
generating the response.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class LLMService(ABC):
    """Provider-agnostic LLM interface."""

    # Default system prompt — can be overridden per-provider or at init
    DEFAULT_SYSTEM_PROMPT = (
        "You are an AI sales assistant for a professional services company.\n"
        "Your job is to:\n"
        "1. Greet the caller warmly\n"
        "2. Understand what they need\n"
        "3. Qualify them as a lead (ask about budget, timeline, decision-making authority)\n"
        "4. Book an appointment if they're interested\n"
        "5. Be conversational, helpful, and professional\n"
        "\n"
        "Keep your responses concise and natural — this is a voice conversation, not an essay.\n"
        "Aim for 1-3 sentences per response. Ask one question at a time."
    )

    def __init__(self, system_prompt: str | None = None):
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name shown in /health."""
        ...

    @abstractmethod
    async def generate_response(
        self,
        message: str,
        conversation: list[dict] | None = None,
    ) -> str:
        """
        Generate an AI response.

        Args:
            message:      The latest user message.
            conversation: Previous turns as [{"role": "user"|"assistant", "content": "..."}].

        Returns:
            The model's text response.
        """
        ...

    async def stream_response(
        self,
        message: str,
        conversation: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream an AI response token-by-token.

        Default implementation: calls generate_response() and yields the
        full text as a single chunk.  Providers that support native streaming
        (e.g. Gemini) should override this for real token-level streaming.

        Yields:
            Text chunks (tokens or partial sentences).
        """
        full = await self.generate_response(message, conversation)
        yield full
