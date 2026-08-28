"""
Scripted fallback agent.
========================
A deterministic keyword-matching "agent" that simulates a sales conversation.
Used when no LLM provider is configured so the voice loop still works at $0.
"""

from __future__ import annotations

from backend.llm.base import LLMService


class ScriptedService(LLMService):
    """Zero-cost fallback — no API calls, just if/elif."""

    @property
    def provider_name(self) -> str:
        return "scripted (fallback)"

    async def generate_response(
        self,
        message: str,
        conversation: list[dict] | None = None,
    ) -> str:
        msg = message.lower()
        turn_count = len(conversation) if conversation else 0

        if turn_count == 0 or any(
            w in msg for w in ["hi", "hello", "hey", "good morning", "good afternoon"]
        ):
            return (
                "Hello! Welcome — I'm your AI sales assistant. "
                "How can I help you today?"
            )

        if any(w in msg for w in ["appointment", "book", "schedule", "meeting", "call"]):
            return (
                "I'd be happy to help you book an appointment! "
                "What day works best for you?"
            )

        if any(
            w in msg
            for w in [
                "monday", "tuesday", "wednesday", "thursday", "friday",
                "saturday", "sunday", "tomorrow", "today", "next week",
            ]
        ):
            return "Great choice. What time would you prefer — morning or afternoon?"

        if any(
            w in msg
            for w in ["morning", "afternoon", "evening", "10", "11", "2", "3", "pm", "am"]
        ):
            return (
                "Perfect. I have that slot available. "
                "Can I get your name and email to confirm the booking?"
            )

        if "@" in msg or any(
            w in msg for w in ["name is", "my name", "email", "phone", "number"]
        ):
            return (
                "Thank you! I've noted your details. "
                "Your appointment is confirmed. "
                "Is there anything else I can help you with?"
            )

        if any(w in msg for w in ["price", "cost", "pricing", "how much", "budget"]):
            return (
                "Our services start at various price points depending on your needs. "
                "Would you like to schedule a consultation to discuss specifics?"
            )

        if any(w in msg for w in ["bye", "thank", "thanks", "goodbye", "that's all"]):
            return (
                "Thank you for your time! "
                "If you need anything else, don't hesitate to reach out. Have a great day!"
            )

        return (
            f'I understand you said: "{message}". '
            "Could you tell me more about what you're looking for? "
            "I'm here to help with appointments, pricing, or any questions."
        )
