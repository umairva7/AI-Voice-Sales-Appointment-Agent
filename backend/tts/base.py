"""
Abstract base class for all TTS providers.
===========================================
Every provider implements this interface.
The chat endpoints only talk to this interface — swapping providers
requires zero changes to the rest of the codebase.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TTSService(ABC):
    """Provider-agnostic TTS interface."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name shown in /health."""
        ...

    @property
    def is_server_side(self) -> bool:
        """Whether this provider generates audio on the server."""
        return False

    @abstractmethod
    async def synthesize(self, text: str) -> bytes | None:
        """
        Convert text to audio bytes.

        Args:
            text: The text to speak.

        Returns:
            MP3 audio bytes, or None if TTS is handled client-side.
        """
        ...
