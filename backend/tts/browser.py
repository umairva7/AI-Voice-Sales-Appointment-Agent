"""
Browser-based TTS (no-op server-side).
=======================================
Signals the frontend to use the SpeechSynthesis API.
No server resources consumed — all TTS happens in the browser.
"""

from __future__ import annotations

from backend.tts.base import TTSService


class BrowserTTSService(TTSService):
    """Zero-cost TTS — delegates to the browser's SpeechSynthesis API."""

    @property
    def provider_name(self) -> str:
        return "browser (SpeechSynthesis)"

    @property
    def is_server_side(self) -> bool:
        return False

    async def synthesize(self, text: str) -> bytes | None:
        # Client handles TTS — nothing to do server-side
        return None
