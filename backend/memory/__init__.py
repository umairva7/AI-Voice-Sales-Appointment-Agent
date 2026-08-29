"""
Conversation Memory Layer
==========================
Server-side conversation memory with session management.

Usage:
    from backend.memory import ConversationMemory

    memory = ConversationMemory()
    session_id = memory.create_session()
    memory.add_turn(session_id, "user", "I want to book an appointment.")
    memory.add_turn(session_id, "assistant", "Sure. What day?")
    history = memory.get_history(session_id)
"""

from backend.memory.manager import ConversationMemory

__all__ = ["ConversationMemory"]
