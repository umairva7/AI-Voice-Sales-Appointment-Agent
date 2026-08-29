"""
Conversation Memory Manager
=============================
Server-side conversation state per session.

Each session maintains:
  • A rolling list of {role, content} turns
  • Metadata (created_at, last_active, turn_count)
  • Automatic pruning when the window exceeds max_turns

Sessions expire after a configurable TTL so we don't leak memory.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional


@dataclass
class Session:
    """A single conversation session."""

    session_id: str
    turns: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    @property
    def turn_count(self) -> int:
        return len(self.turns)


class ConversationMemory:
    """
    Thread-safe, in-memory conversation store.

    Designed for Phase 2 — keeps conversation history server-side
    so the LLM sees the full context window on every request.

    Features:
        • Session-based isolation (each caller gets their own history)
        • Sliding window (oldest turns are dropped when max_turns exceeded)
        • TTL-based cleanup (stale sessions auto-expire)
        • Summary of pruned turns (so the LLM doesn't lose critical context)
    """

    def __init__(
        self,
        max_turns: int = 50,
        session_ttl_seconds: int = 3600,  # 1 hour
    ):
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()
        self.max_turns = max_turns
        self.session_ttl = session_ttl_seconds

    # ── Session lifecycle ────────────────────────────────────

    def create_session(self, session_id: str | None = None) -> str:
        """
        Create a new conversation session.

        Returns the session_id (auto-generated if not provided).
        """
        sid = session_id or uuid.uuid4().hex[:16]
        with self._lock:
            self._sessions[sid] = Session(session_id=sid)
        return sid

    def get_or_create_session(self, session_id: str | None = None) -> str:
        """
        Return existing session or create a new one.

        This is the main entry point — the /chat endpoint calls this
        with whatever session_id the client sends (or None for a new one).
        """
        if session_id and session_id in self._sessions:
            return session_id
        return self.create_session(session_id)

    def session_exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its history. Returns True if it existed."""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    # ── Turn management ──────────────────────────────────────

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """
        Append a turn to the conversation.

        Args:
            session_id: The session to append to (must exist).
            role:       "user" or "assistant"
            content:    The message text.

        Raises:
            KeyError if session doesn't exist.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Session {session_id!r} not found")

            session.turns.append({
                "role": role,
                "content": content,
            })
            session.last_active = time.time()

            # Prune if we exceed the window
            if len(session.turns) > self.max_turns:
                self._prune_session(session)

    def get_history(
        self,
        session_id: str,
        last_n: int | None = None,
    ) -> list[dict]:
        """
        Get conversation history for a session.

        Args:
            session_id: Session to retrieve.
            last_n:     If set, return only the last N turns.

        Returns:
            List of {role, content} dicts (shallow copy).
        """
        session = self._sessions.get(session_id)
        if session is None:
            return []

        turns = session.turns
        if last_n is not None:
            turns = turns[-last_n:]
        return [dict(t) for t in turns]  # shallow copy

    def get_session_info(self, session_id: str) -> dict | None:
        """Return metadata about a session (for debugging / API)."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        return {
            "session_id": session.session_id,
            "turn_count": session.turn_count,
            "created_at": session.created_at,
            "last_active": session.last_active,
            "age_seconds": time.time() - session.created_at,
        }

    # ── Housekeeping ─────────────────────────────────────────

    def cleanup_stale_sessions(self) -> int:
        """
        Remove sessions that have been inactive longer than the TTL.

        Returns the number of sessions removed.
        Call this periodically (e.g. from a background task).
        """
        now = time.time()
        stale_ids = []

        with self._lock:
            for sid, session in self._sessions.items():
                if now - session.last_active > self.session_ttl:
                    stale_ids.append(sid)

            for sid in stale_ids:
                del self._sessions[sid]

        if stale_ids:
            print(f"[Memory] Cleaned up {len(stale_ids)} stale session(s)")

        return len(stale_ids)

    @property
    def active_session_count(self) -> int:
        return len(self._sessions)

    def list_sessions(self) -> list[dict]:
        """List all active sessions with metadata."""
        return [
            self.get_session_info(sid)
            for sid in self._sessions
            if self.get_session_info(sid)
        ]

    # ── Internal ─────────────────────────────────────────────

    def _prune_session(self, session: Session) -> None:
        """
        Sliding window: keep only the last `max_turns` turns.

        The pruned turns are summarised into a single system message
        so the LLM retains awareness of early context.
        """
        overflow = len(session.turns) - self.max_turns
        if overflow <= 0:
            return

        pruned = session.turns[:overflow]
        session.turns = session.turns[overflow:]

        # Build a compact summary of what was pruned
        summary_lines = []
        for turn in pruned:
            role_label = "User" if turn["role"] == "user" else "AI"
            # Truncate long messages in the summary
            content = turn["content"][:100]
            if len(turn["content"]) > 100:
                content += "…"
            summary_lines.append(f"  {role_label}: {content}")

        summary_text = (
            "[Earlier conversation context — summarised]\n"
            + "\n".join(summary_lines)
        )

        # Prepend the summary as a system-like context turn
        session.turns.insert(0, {
            "role": "user",  # using "user" role since not all providers support "system" in-line
            "content": summary_text,
        })

        print(
            f"[Memory] Session {session.session_id}: "
            f"pruned {overflow} turn(s), {len(session.turns)} remaining"
        )
