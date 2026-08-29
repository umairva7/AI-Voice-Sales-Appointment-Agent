"""
Edge TTS provider (free Microsoft voices via edge-tts package).
================================================================
Uses the same voices as Microsoft Edge's Read Aloud feature.
Completely free — no API key required.

Env vars:
    TTS_PROVIDER=edge
    TTS_VOICE=en-US-AriaNeural   (default)
"""

from __future__ import annotations

import io

from backend.tts.base import TTSService


class EdgeTTSService(TTSService):
    """Free, high-quality TTS using Microsoft Edge voices."""

    def __init__(self, voice: str = "en-US-AriaNeural"):
        self.voice = voice

    @property
    def provider_name(self) -> str:
        return f"edge-tts ({self.voice})"

    @property
    def is_server_side(self) -> bool:
        return True

    async def synthesize(self, text: str) -> bytes | None:
        import edge_tts

        communicate = edge_tts.Communicate(text, self.voice)
        buffer = io.BytesIO()

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])

        audio_bytes = buffer.getvalue()
        return audio_bytes if audio_bytes else None
