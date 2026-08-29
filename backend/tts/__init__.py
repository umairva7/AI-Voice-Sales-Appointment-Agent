"""
TTS Service Layer
=================
Provider-agnostic interface for text-to-speech.

Usage:
    from backend.tts import create_tts_service

    tts = create_tts_service()  # reads from env
    audio = await tts.synthesize("Hello!")
"""

import os

from backend.tts.base import TTSService


def create_tts_service() -> TTSService:
    """
    Factory: build the right TTS service from environment variables.

    TTS_PROVIDER env var:
        "edge"    → EdgeTTSService (free, server-side)
        "browser" → BrowserTTSService (client-side, default)
    """
    provider = os.getenv("TTS_PROVIDER", "browser").lower()

    if provider == "edge":
        from backend.tts.edge import EdgeTTSService

        voice = os.getenv("TTS_VOICE", "en-US-AriaNeural")
        print(f"[TTS] Using Edge TTS — voice: {voice}")
        return EdgeTTSService(voice=voice)

    from backend.tts.browser import BrowserTTSService

    print("[TTS] Using browser SpeechSynthesis (client-side)")
    return BrowserTTSService()


__all__ = ["create_tts_service", "TTSService"]
