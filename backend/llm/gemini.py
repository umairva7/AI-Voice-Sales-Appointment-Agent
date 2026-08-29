"""
Google Gemini provider.
=======================
Calls the Gemini REST API directly via httpx — no heavy SDK required.

Env vars:
    GEMINI_API_KEY   — your API key
    LLM_MODEL        — model name (default: gemini-2.0-flash)
"""

from __future__ import annotations

import httpx

from backend.llm.base import LLMService


class GeminiService(LLMService):
    """Gemini via the generativelanguage.googleapis.com REST API."""

    API_BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-flash-latest",
        system_prompt: str | None = None,
    ):
        super().__init__(system_prompt)
        self.api_key = api_key
        self.model = model

    @property
    def provider_name(self) -> str:
        return f"gemini ({self.model})"

    async def generate_response(
        self,
        message: str,
        conversation: list[dict] | None = None,
    ) -> str:
        """
        Call Gemini's generateContent endpoint.

        Converts our standard conversation format:
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

        Into Gemini's format:
            [{"role": "user", "parts": [{"text": "..."}]}, {"role": "model", "parts": [{"text": "..."}]}]
        """
        url = f"{self.API_BASE}/models/{self.model}:generateContent"

        # Build Gemini-format contents
        contents = []

        # System instruction goes as a separate field (not in contents)
        system_instruction = {
            "parts": [{"text": self.system_prompt}]
        }

        # Add conversation history
        if conversation:
            for turn in conversation:
                role = "model" if turn["role"] == "assistant" else "user"
                contents.append({
                    "role": role,
                    "parts": [{"text": turn["content"]}],
                })

        # Add the current user message
        contents.append({
            "role": "user",
            "parts": [{"text": message}],
        })

        payload = {
            "system_instruction": system_instruction,
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 256,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": self.api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract text from Gemini's response structure
        try:
            return (
                data["candidates"][0]["content"]["parts"][0]["text"].strip()
            )
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected Gemini response shape: {e}") from e
