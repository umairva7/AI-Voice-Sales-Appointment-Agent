"""
LLM Service Layer
=================
Provider-agnostic interface for language model access.

Usage:
    from backend.llm import create_llm_service

    service = create_llm_service()  # reads from env
    reply = await service.generate_response("Hello", conversation=[])
"""

from backend.llm.factory import create_llm_service
from backend.llm.base import LLMService

__all__ = ["create_llm_service", "LLMService"]
