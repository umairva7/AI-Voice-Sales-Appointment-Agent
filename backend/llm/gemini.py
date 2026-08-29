from __future__ import annotations

import json as _json
from collections.abc import AsyncGenerator

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

    # ── Shared payload builder ───────────────────────────────

    def _build_payload(
        self,
        message: str,
        conversation: list[dict] | None = None,
    ) -> dict:
        """Build the Gemini request payload (shared by both endpoints)."""
        contents = []

        system_instruction = {
            "parts": [{"text": self.system_prompt}]
        }

        if conversation:
            for turn in conversation:
                role = "model" if turn["role"] == "assistant" else "user"
                contents.append({
                    "role": role,
                    "parts": [{"text": turn["content"]}],
                })

        contents.append({
            "role": "user",
            "parts": [{"text": message}],
        })

        return {
            "system_instruction": system_instruction,
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 256,
            },
        }

    # ── Non-streaming (original) ─────────────────────────────

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
        payload = self._build_payload(message, conversation)

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

    # ── Streaming ────────────────────────────────────────────

    async def stream_response(
        self,
        message: str,
        conversation: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream from Gemini's streamGenerateContent endpoint (SSE).

        Yields text deltas as they arrive from the API.
        """
        url = f"{self.API_BASE}/models/{self.model}:streamGenerateContent"
        payload = self._build_payload(message, conversation)

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": self.api_key,
                },
                params={"alt": "sse"},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = _json.loads(data_str)
                        text = (
                            chunk["candidates"][0]["content"]["parts"][0]["text"]
                        )
                        if text:
                            yield text
                    except (KeyError, IndexError, _json.JSONDecodeError):
                        continue
