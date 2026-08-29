"""
LLM Service Factory
====================
Reads env vars and returns the correct LLMService implementation.

Priority:
    1. GEMINI_API_KEY set           → GeminiService
    2. LLM_PROVIDER + LLM_API_KEY  → OpenAICompatibleService
    3. Neither                      → ScriptedService (fallback)

This is the ONLY place that knows about concrete provider classes.
Everything else programs to the LLMService interface.
"""

from __future__ import annotations

import os

from backend.llm.base import LLMService


def create_llm_service() -> LLMService:
    """
    Factory: build the right LLM service from environment variables.

    Returns a ready-to-use LLMService instance.
    """

    # ── 1. Gemini ────────────────────────────────────────────
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if gemini_key:
        from backend.llm.gemini import GeminiService

        model = os.getenv("LLM_MODEL", "gemini-flash-latest")
        print(f"[LLM] Using Gemini provider — model: {model}")
        return GeminiService(api_key=gemini_key, model=model)

    # ── 2. OpenAI-compatible (OpenAI / GitHub / Groq / Ollama) ─
    provider = os.getenv("LLM_PROVIDER", "").lower()
    api_key = os.getenv("LLM_API_KEY", "")

    if provider and api_key:
        from backend.llm.openai_compat import OpenAICompatibleService

        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        base_url = os.getenv("LLM_BASE_URL", "")
        print(f"[LLM] Using {provider} provider — model: {model}")
        return OpenAICompatibleService(
            api_key=api_key,
            model=model,
            base_url=base_url or None,
            provider_label=provider,
        )

    # ── 3. Fallback ──────────────────────────────────────────
    from backend.llm.scripted import ScriptedService

    print("[LLM] No provider configured — using scripted fallback")
    return ScriptedService()
