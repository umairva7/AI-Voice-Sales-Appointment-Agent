"""
AI Voice Sales Agent — Phase 1 Backend
=======================================
FastAPI server that:
  1. Serves the frontend static files
  2. Provides POST /api/chat for the voice loop
  3. Maintains conversation context per request
  4. Integrates with an LLM (GitHub Models / OpenAI-compatible)
  5. Falls back to a scripted echo agent when no LLM is configured

Run:
    uvicorn backend.main:app --reload --port 8000

Or from project root:
    python -m uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import os
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

# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="AI Voice Agent API",
    description="Phase 1 push-to-talk voice loop",
    version="1.0.0",
)

# CORS — allow the frontend (served from same origin, but also dev scenarios)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ───────────────────────────────────────────────────

class MessageRequest(BaseModel):
    message: str
    history: Optional[list[dict]] = None


class ChatResponse(BaseModel):
    reply: str


# ── LLM integration ─────────────────────────────────────────
# Configure via .env:
#   LLM_PROVIDER=github   (or "openai")
#   LLM_API_KEY=your_token
#   LLM_MODEL=gpt-4o-mini  (or any model name)
#   LLM_BASE_URL=https://models.inference.ai.azure.com  (for GitHub Models)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").lower()
LLM_API_KEY  = os.getenv("LLM_API_KEY", "")
LLM_MODEL    = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")

# System prompt — defines the sales agent persona
SYSTEM_PROMPT = """You are an AI sales assistant for a professional services company.
Your job is to:
1. Greet the caller warmly
2. Understand what they need
3. Qualify them as a lead (ask about budget, timeline, decision-making authority)
4. Book an appointment if they're interested
5. Be conversational, helpful, and professional

Keep your responses concise and natural — this is a voice conversation, not an essay.
Aim for 1-3 sentences per response. Ask one question at a time.
"""


async def get_llm_response(message: str, history: list[dict] | None = None) -> str:
    """
    Route to the configured LLM provider.
    Falls back to a scripted echo if no provider is configured.
    """
    if LLM_PROVIDER in ("github", "openai") and LLM_API_KEY:
        return await _call_openai_compatible(message, history)

    # ── Fallback: scripted echo agent ────────────────────────
    return _scripted_agent(message, history)


async def _call_openai_compatible(
    message: str, history: list[dict] | None = None
) -> str:
    """Call an OpenAI-compatible API (works with GitHub Models too)."""
    try:
        from openai import AsyncOpenAI

        base_url = LLM_BASE_URL or (
            "https://models.inference.ai.azure.com"
            if LLM_PROVIDER == "github"
            else None
        )

        client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=base_url)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        completion = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=256,
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        print(f"[LLM Error] {e}")
        return _scripted_agent(message, history)


def _scripted_agent(message: str, history: list[dict] | None = None) -> str:
    """
    A deterministic fallback agent that simulates a sales conversation.
    Good enough for testing the voice loop without an LLM key.
    """
    msg_lower = message.lower()
    turn_count = len(history) if history else 0

    # Greeting
    if turn_count == 0 or any(
        w in msg_lower for w in ["hi", "hello", "hey", "good morning", "good afternoon"]
    ):
        return (
            "Hello! Welcome — I'm your AI sales assistant. "
            "How can I help you today?"
        )

    # Appointment intent
    if any(w in msg_lower for w in ["appointment", "book", "schedule", "meeting", "call"]):
        return (
            "I'd be happy to help you book an appointment! "
            "What day works best for you?"
        )

    # Day mentioned
    if any(
        w in msg_lower
        for w in [
            "monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "sunday", "tomorrow", "today", "next week",
        ]
    ):
        return "Great choice. What time would you prefer — morning or afternoon?"

    # Time mentioned
    if any(
        w in msg_lower
        for w in ["morning", "afternoon", "evening", "10", "11", "2", "3", "pm", "am"]
    ):
        return (
            "Perfect. I have that slot available. "
            "Can I get your name and email to confirm the booking?"
        )

    # Contact info
    if "@" in msg_lower or any(
        w in msg_lower for w in ["name is", "my name", "email", "phone", "number"]
    ):
        return (
            "Thank you! I've noted your details. "
            "Your appointment is confirmed. "
            "Is there anything else I can help you with?"
        )

    # Pricing / cost
    if any(w in msg_lower for w in ["price", "cost", "pricing", "how much", "budget"]):
        return (
            "Our services start at various price points depending on your needs. "
            "Would you like to schedule a consultation to discuss specifics?"
        )

    # Goodbye
    if any(w in msg_lower for w in ["bye", "thank", "thanks", "goodbye", "that's all"]):
        return (
            "Thank you for your time! "
            "If you need anything else, don't hesitate to reach out. Have a great day!"
        )

    # Fallback
    return (
        f'I understand you said: "{message}". '
        "Could you tell me more about what you're looking for? "
        "I'm here to help with appointments, pricing, or any questions."
    )


# ── Routes ───────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    """Serve the main HTML page."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "llm_configured": bool(LLM_PROVIDER and LLM_API_KEY),
    }


@app.post("/api/chat", tags=["Chat"], response_model=ChatResponse)
async def chat(request: MessageRequest) -> ChatResponse:
    """
    Main chat endpoint.
    Accepts the user message + optional conversation history,
    returns the AI response.
    """
    message = request.message.strip()
    if not message:
        return ChatResponse(reply="I didn't catch that. Could you try again?")

    reply = await get_llm_response(message, request.history)
    return ChatResponse(reply=reply)


# Alias for backward compatibility
@app.post("/api/message", tags=["Chat"], include_in_schema=False)
async def handle_message(request: MessageRequest) -> ChatResponse:
    return await chat(request)


# ── Static files (must be last) ──────────────────────────────
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
