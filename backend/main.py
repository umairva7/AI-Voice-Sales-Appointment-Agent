"""
AI Voice Sales Agent — Phase 1 Backend
=======================================
FastAPI server that:
  1. Serves the frontend static files
  2. Provides POST /api/chat for the voice loop
  3. Delegates to an LLM service (Gemini / OpenAI / Groq / Ollama / scripted)

The /chat endpoint doesn't know or care which model is responding.

Run:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
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

# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="AI Voice Agent API",
    description="Phase 1 push-to-talk voice loop",
    version="1.0.0",
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
    history: Optional[list[dict]] = None


class ChatResponse(BaseModel):
    reply: str


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
        "provider": llm_service.provider_name,
    }


@app.post("/api/chat", tags=["Chat"], response_model=ChatResponse)
async def chat(request: MessageRequest) -> ChatResponse:
    """
    Main chat endpoint.
    Accepts the user's message + conversation history,
    delegates to whatever LLM service is configured,
    returns the response.

    The endpoint doesn't know whether Gemini, GPT, Groq,
    or a scripted fallback generated the reply.
    """
    message = request.message.strip()
    if not message:
        return ChatResponse(reply="I didn't catch that. Could you try again?")

    try:
        reply = await llm_service.generate_response(message, request.history)
    except Exception as e:
        print(f"[LLM Error] {e}")
        # Fall back to scripted if the real provider fails
        from backend.llm.scripted import ScriptedService
        fallback = ScriptedService()
        reply = await fallback.generate_response(message, request.history)

    return ChatResponse(reply=reply)


# Alias for backward compatibility
@app.post("/api/message", tags=["Chat"], include_in_schema=False)
async def handle_message(request: MessageRequest) -> ChatResponse:
    return await chat(request)


# ── Static files (must be last) ──────────────────────────────
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
