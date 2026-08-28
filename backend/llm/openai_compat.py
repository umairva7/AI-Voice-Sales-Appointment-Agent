"""
OpenAI-compatible provider.
============================
Works with any API that speaks the OpenAI chat completions format:
  • OpenAI          (api.openai.com)
  • GitHub Models   (models.inference.ai.azure.com)
  • Groq            (api.groq.com/openai)
  • Ollama          (localhost:11434/v1)
  • Together AI, Fireworks, etc.

Just change the base_url and api_key.

Env vars:
    LLM_API_KEY    — API key / token
    LLM_MODEL      — model name (default: gpt-4o-mini)
    LLM_BASE_URL   — API base URL (optional, defaults per provider)
"""

from __future__ import annotations

from backend.llm.base import LLMService


# Known base URLs for convenience
KNOWN_BASE_URLS = {
    "openai":  None,  # openai SDK default
    "github":  "https://models.inference.ai.azure.com",
    "groq":    "https://api.groq.com/openai/v1",
    "ollama":  "http://localhost:11434/v1",
}


class OpenAICompatibleService(LLMService):
    """Any provider that speaks the OpenAI chat completions protocol."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        provider_label: str = "openai",
        system_prompt: str | None = None,
    ):
        super().__init__(system_prompt)
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or KNOWN_BASE_URLS.get(provider_label)
        self._provider_label = provider_label

    @property
    def provider_name(self) -> str:
        return f"{self._provider_label} ({self.model})"

    async def generate_response(
        self,
        message: str,
        conversation: list[dict] | None = None,
    ) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        messages = [{"role": "system", "content": self.system_prompt}]
        if conversation:
            messages.extend(conversation)
        messages.append({"role": "user", "content": message})

        completion = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=256,
        )

        return completion.choices[0].message.content.strip()
