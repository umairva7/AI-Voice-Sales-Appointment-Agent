# AI Voice Sales & Appointment Agent

An end-to-end AI voice agent that can communicate with leads, understand their intent, qualify them, manage CRM data, book appointments, and trigger automated follow-up workflows.

The project is being built as a practical learning project to explore **AI agents, voice AI, CRM automation, REST APIs, webhooks, and backend engineering**.

---

## Phase 2 — Streaming Voice Agent ✅

Upgrades the Phase 1 prototype into a structured voice AI agent with:

- **WebSocket streaming** — real-time token-by-token responses via `WS /ws/chat`
- **Conversation memory** — server-side session management with sliding window & TTL cleanup
- **LLM service abstraction** — hot-swappable providers (Gemini / OpenAI / Groq / Ollama / scripted fallback)
- **Streaming LLM responses** — Gemini `streamGenerateContent` SSE → live token delivery
- **TTS abstraction** — swappable TTS layer (browser SpeechSynthesis now, Edge TTS ready)
- **HTTP fallback** — frontend automatically falls back to `POST /api/chat` if WebSocket fails

```text
You: 🎙️ "Hi, I want to book an appointment."

System (streaming):
  You: Hi, I want to book an appointment.
  AI:  S|u|r|e|,| |I|'|d| |b|e| |h|a|p|p|y| ... (tokens stream in real-time)

🔊 Browser speaks the complete response aloud.
```

### Architecture

```text
┌─────────────────────┐
│   Browser UI        │
│   🎙 Start Speaking │
└──────────┬──────────┘
           │ microphone
           ▼
┌─────────────────────┐
│ Speech-to-Text      │
│ Web Speech API      │
└──────────┬──────────┘
           │ text
           ▼
┌─────────────────────────────┐
│ Backend (FastAPI)           │
│ WS  /ws/chat  (streaming)  │◄── preferred
│ POST /api/chat (fallback)  │◄── automatic fallback
│ → LLM Service → Memory     │
└──────────┬──────────────────┘
           │ streamed tokens / text
           ▼
┌─────────────────────┐
│ Text-to-Speech      │
│ SpeechSynthesis API │
└──────────┬──────────┘
           │ audio
           ▼
      🔊 User hears
```

### Stack

| Part       | Technology                        | Why                          |
| ---------- | --------------------------------- | ---------------------------- |
| Frontend   | HTML + CSS + JavaScript           | Simple, no framework bloat   |
| Microphone | Web Speech API                    | Built into browser           |
| STT        | Web Speech API                    | Free                         |
| Backend    | FastAPI + Python                  | Matches existing skills      |
| Transport  | WebSocket (WS) + HTTP fallback    | Streaming + reliability      |
| AI         | Gemini 2.5 Flash (configurable)   | Free tier, hot-swappable     |
| Memory     | Server-side sessions              | Sliding window + TTL cleanup |
| TTS        | Browser SpeechSynthesis / Edge    | Free, swappable              |
| Hosting    | Localhost                         | $0                           |

### Milestones Implemented

- [x] 1️⃣ Browser microphone capture
- [x] 2️⃣ Speech-to-text transcription in UI
- [x] 3️⃣ FastAPI backend (`POST /api/chat` + `WS /ws/chat`)
- [x] 4️⃣ LLM service abstraction (factory pattern, hot-swappable)
- [x] 5️⃣ Streaming LLM responses (Gemini SSE)
- [x] 6️⃣ Text-to-speech response
- [x] 7️⃣ Server-side conversation memory (sessions, sliding window, TTL)
- [x] 8️⃣ WebSocket communication with HTTP fallback
- [x] 9️⃣ TTS service abstraction (browser + edge-tts ready)

---

## Project Structure

```
AI-voice-agent/
│
├── backend/
│   ├── main.py              # FastAPI server + REST + WebSocket endpoints
│   ├── requirements.txt     # Python dependencies
│   ├── .env                 # LLM/TTS config (gitignored)
│   ├── __init__.py
│   │
│   ├── llm/                 # LLM service layer
│   │   ├── __init__.py      # Factory export
│   │   ├── base.py          # Abstract LLMService interface
│   │   ├── factory.py       # Provider selection from env vars
│   │   ├── gemini.py        # Gemini provider (streaming + non-streaming)
│   │   ├── openai_compat.py # OpenAI-compatible provider
│   │   └── scripted.py      # Zero-cost scripted fallback
│   │
│   ├── memory/              # Conversation memory layer
│   │   ├── __init__.py
│   │   └── manager.py       # Session-based memory with sliding window
│   │
│   └── tts/                 # TTS service layer
│       ├── __init__.py      # Factory export
│       ├── base.py          # Abstract TTSService interface
│       ├── browser.py       # Browser SpeechSynthesis (client-side)
│       └── edge.py          # Edge TTS (free server-side, optional)
│
├── frontend/
│   ├── index.html           # Voice agent UI
│   ├── style.css            # Design system
│   └── script.js            # STT + WebSocket + HTTP fallback + TTS
│
├── .gitignore
└── README.md
```

---

## Quick Start

### 1. Install dependencies

```bash
cd AI-voice-agent
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

pip install -r backend/requirements.txt
```

### 2. (Optional) Configure an LLM

Edit `backend/.env` and uncomment/fill in your keys:

```env
# Gemini (default — free tier)
GEMINI_API_KEY=your_gemini_api_key
LLM_MODEL=gemini-flash-latest

# GitHub Models (free with GitHub Student)
# LLM_PROVIDER=github
# LLM_API_KEY=your_github_token
# LLM_MODEL=gpt-4o-mini
# LLM_BASE_URL=https://models.inference.ai.azure.com
```

> **Without an LLM key**, the agent uses a built-in scripted fallback that simulates a sales conversation. The full voice loop still works.

### 3. (Optional) Configure TTS

```env
# Default: browser SpeechSynthesis (no config needed)
# TTS_PROVIDER=browser

# Edge TTS (free, server-side, higher quality)
# TTS_PROVIDER=edge
# TTS_VOICE=en-US-AriaNeural
```

### 4. Run the server

```bash
uvicorn backend.main:app --reload --port 8000
```

### 5. Open in browser

Navigate to **http://localhost:8000** in **Chrome** or **Edge** (required for Web Speech API).

Click the microphone → speak → watch tokens stream in real-time → hear the AI respond.

---

## API Reference

### `GET /health`

Health check. Returns `{ "status": "healthy", "llm_provider": "...", "tts_provider": "...", "active_sessions": 0 }`.

### `POST /api/chat`

Main chat endpoint (HTTP, non-streaming).

**Request:**
```json
{
  "message": "I want to book an appointment",
  "session_id": "abc123"
}
```

**Response:**
```json
{
  "reply": "I'd be happy to help you book an appointment! What day works best for you?",
  "session_id": "abc123"
}
```

### `WS /ws/chat`

WebSocket endpoint for streaming chat.

**Client sends:**
```json
{"type": "message", "message": "I want to book an appointment", "session_id": "abc123"}
```

**Server streams back:**
```json
{"type": "stream_start"}
{"type": "token", "content": "I'd"}
{"type": "token", "content": " be happy"}
{"type": "token", "content": " to help..."}
{"type": "stream_end", "full_reply": "I'd be happy to help...", "session_id": "abc123", "tts_mode": "browser"}
```

### Session Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/session` | POST | Create a new session |
| `/api/session/{id}` | GET | Get session metadata |
| `/api/session/{id}/history` | GET | Get conversation history |
| `/api/session/{id}` | DELETE | Delete a session |
| `/api/sessions` | GET | List all active sessions |

---

## Future Phases

### Phase 3 — CRM Integration
- GoHighLevel API integration
- Lead qualification & scoring
- Appointment management
- Webhook event handling

### Phase 4 — Automation
- Follow-up sequences
- Appointment reminders
- Sales notifications
- Human handoff

---

## Full Architecture (Target)

```text
                         ┌───────────────────┐
                         │   Lead / Caller   │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │  Browser Voice UI │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │ Speech-to-Text    │
                         └─────────┬─────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │       AI Voice Agent        │
                    │                             │
                    │  Intent Detection           │
                    │  Conversation Context       │
                    │  Lead Qualification         │
                    │  Tool Calling               │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │   FastAPI Backend │
                         └─────────┬─────────┘
                                   │
                  ┌────────────────┼────────────────┐
                  │                │                │
                  ▼                ▼                ▼
             ┌─────────┐    ┌────────────┐   ┌──────────┐
             │   GHL   │    │  Database  │   │ Webhooks │
             │   API   │    │            │   │          │
             └────┬────┘    └────────────┘   └────┬─────┘
                  │                                │
                  ▼                                │
          ┌─────────────────┐                     │
          │ CRM & Pipeline  │◄────────────────────┘
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │    Workflows    │
          └────────┬────────┘
                   │
          ┌────────┴─────────┐
          ▼                  ▼
     Follow-up            Reminder
          │                  │
          └────────┬─────────┘
                   ▼
                  Lead
```