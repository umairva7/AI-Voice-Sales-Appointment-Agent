"""
AI Voice Sales Agent — Phase 2 Backend
=======================================
FastAPI server that:
  1. Serves the frontend static files
  2. Provides POST /api/chat for the voice loop (with server-side memory)
  3. Provides WS /ws/chat for streaming responses
  4. Provides session management endpoints
  5. Delegates to an LLM service (Gemini / OpenAI / Groq / Ollama / scripted)
  6. Delegates TTS to a TTS service (browser / edge-tts)
  7. Runs background cleanup for stale sessions

The chat endpoints don't know or care which model is responding.
Conversation history is maintained server-side per session.

Run:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Load env vars ────────────────────────────────────────────
load_dotenv()

# ── Paths ────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# ── LLM Service (created once at startup) ────────────────────
from backend.llm import create_llm_service  # noqa: E402

llm_service = create_llm_service()

# ── TTS Service (created once at startup) ────────────────────
from backend.tts import create_tts_service  # noqa: E402

tts_service = create_tts_service()

# ── Conversation Memory (server-side) ────────────────────────
from backend.memory import ConversationMemory  # noqa: E402

memory = ConversationMemory(
    max_turns=50,
    session_ttl_seconds=3600,  # 1 hour
)


# ── Background session cleanup ───────────────────────────────

async def _cleanup_loop():
    """Periodically remove stale sessions."""
    while True:
        await asyncio.sleep(300)  # every 5 minutes
        memory.cleanup_stale_sessions()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    task = asyncio.create_task(_cleanup_loop())
    print("[Memory] Background cleanup task started")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    print("[Memory] Background cleanup task stopped")


# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="AI Voice Agent API",
    description="Phase 2 — voice agent with streaming, memory, and TTS abstraction",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ────────────────────────────────

class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    # Legacy field — still accepted but server-side memory takes priority
    history: Optional[list[dict]] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class SessionResponse(BaseModel):
    session_id: str
    turn_count: int
    created_at: float
    last_active: float
    age_seconds: float


class SessionHistoryResponse(BaseModel):
    session_id: str
    turns: list[dict]
    turn_count: int


# ── Routes ───────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    """Serve the main HTML page."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check — shows which LLM provider is active."""
    return {
        "status": "healthy",
        "llm_provider": llm_service.provider_name,
        "tts_provider": tts_service.provider_name,
        "active_sessions": memory.active_session_count,
    }


@app.post("/api/chat", tags=["Chat"], response_model=ChatResponse)
async def chat(request: MessageRequest) -> ChatResponse:
    """
    Main chat endpoint.

    Now with server-side conversation memory:
      1. Client sends message + optional session_id
      2. Server looks up (or creates) the session
      3. Appends user turn to memory
      4. Sends full history to the LLM
      5. Appends AI turn to memory
      6. Returns reply + session_id

    The client stores session_id for subsequent requests.
    The endpoint doesn't know whether Gemini, GPT, Groq,
    or a scripted fallback generated the reply.
    """
    message = request.message.strip()
    if not message:
        # Still need a valid session_id for the response
        sid = memory.get_or_create_session(request.session_id)
        return ChatResponse(
            reply="I didn't catch that. Could you try again?",
            session_id=sid,
        )

    # ── 1. Resolve session ───────────────────────────────────
    session_id = memory.get_or_create_session(request.session_id)

    # ── 2. Record user turn ──────────────────────────────────
    memory.add_turn(session_id, "user", message)

    # ── 3. Get full conversation context ─────────────────────
    conversation = memory.get_history(session_id)
    # The history includes the current message as the last turn,
    # so we pass history[:-1] as context and the message separately
    # (matching the LLM service interface)
    context = conversation[:-1] if len(conversation) > 1 else None

    # ── 4. Generate response ─────────────────────────────────
    try:
        reply = await llm_service.generate_response(message, context)
    except Exception as e:
        print(f"[LLM Error] {e}")
        # Fall back to scripted if the real provider fails
        from backend.llm.scripted import ScriptedService
        fallback = ScriptedService()
        reply = await fallback.generate_response(message, context)

    # ── 5. Record AI turn ────────────────────────────────────
    memory.add_turn(session_id, "assistant", reply)

    print(
        f"[Chat] Session {session_id}: "
        f"{memory.get_session_info(session_id)['turn_count']} turns"
    )

    return ChatResponse(reply=reply, session_id=session_id)


# ── Session management endpoints ─────────────────────────────

@app.post("/api/session", tags=["Session"])
async def create_session() -> dict:
    """Create a new conversation session."""
    session_id = memory.create_session()
    return {"session_id": session_id}


@app.get("/api/session/{session_id}", tags=["Session"])
async def get_session(session_id: str) -> SessionResponse:
    """Get session metadata."""
    info = memory.get_session_info(session_id)
    if info is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(**info)


@app.get("/api/session/{session_id}/history", tags=["Session"])
async def get_session_history(
    session_id: str,
    last_n: Optional[int] = None,
) -> SessionHistoryResponse:
    """Get conversation history for a session."""
    if not memory.session_exists(session_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")

    turns = memory.get_history(session_id, last_n=last_n)
    return SessionHistoryResponse(
        session_id=session_id,
        turns=turns,
        turn_count=len(turns),
    )


@app.delete("/api/session/{session_id}", tags=["Session"])
async def delete_session(session_id: str) -> dict:
    """Delete a session and its history."""
    deleted = memory.delete_session(session_id)
    return {"deleted": deleted, "session_id": session_id}


@app.get("/api/sessions", tags=["Session"])
async def list_sessions() -> dict:
    """List all active sessions (debug endpoint)."""
    return {
        "count": memory.active_session_count,
        "sessions": memory.list_sessions(),
    }


# Alias for backward compatibility
@app.post("/api/message", tags=["Chat"], include_in_schema=False)
async def handle_message(request: MessageRequest) -> ChatResponse:
    return await chat(request)


# ── WebSocket streaming endpoint ─────────────────────────────

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat.

    Client sends:
        {"type": "message", "message": "...", "session_id": "..."}

    Server streams back:
        {"type": "stream_start"}
        {"type": "token", "content": "..."}
        {"type": "stream_end", "full_reply": "...", "session_id": "...", "tts_mode": "browser"}
    """
    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") != "message":
                await websocket.send_json(
                    {"type": "error", "message": "Unknown message type"}
                )
                continue

            message = data.get("message", "").strip()
            client_session_id = data.get("session_id")

            if not message:
                sid = memory.get_or_create_session(client_session_id)
                await websocket.send_json({
                    "type": "stream_end",
                    "full_reply": "I didn't catch that. Could you try again?",
                    "session_id": sid,
                    "tts_mode": "browser",
                })
                continue

            # 1. Resolve session
            session_id = memory.get_or_create_session(client_session_id)

            # 2. Record user turn
            memory.add_turn(session_id, "user", message)

            # 3. Get conversation context
            conversation = memory.get_history(session_id)
            context = conversation[:-1] if len(conversation) > 1 else None

            # 4. Stream response
            await websocket.send_json({"type": "stream_start"})

            full_reply = ""
            try:
                async for token in llm_service.stream_response(message, context):
                    full_reply += token
                    await websocket.send_json({
                        "type": "token",
                        "content": token,
                    })
            except Exception as e:
                print(f"[LLM Stream Error] {e}")
                # Fall back to scripted if the real provider fails
                from backend.llm.scripted import ScriptedService

                fallback = ScriptedService()
                full_reply = await fallback.generate_response(message, context)
                await websocket.send_json({
                    "type": "token",
                    "content": full_reply,
                })

            # 5. Record AI turn
            memory.add_turn(session_id, "assistant", full_reply)

            # 6. Send completion
            tts_mode = "server" if tts_service.is_server_side else "browser"
            await websocket.send_json({
                "type": "stream_end",
                "full_reply": full_reply,
                "session_id": session_id,
                "tts_mode": tts_mode,
            })

            print(
                f"[WS Chat] Session {session_id}: "
                f"{memory.get_session_info(session_id)['turn_count']} turns"
            )

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS Error] {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass


# ── Static files (must be last) ──────────────────────────────
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
