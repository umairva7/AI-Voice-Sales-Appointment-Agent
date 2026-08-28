# AI Voice Sales & Appointment Agent

An end-to-end AI voice agent that can communicate with leads, understand their intent, qualify them, manage CRM data, book appointments, and trigger automated follow-up workflows.

The project is being built as a practical learning project to explore **AI agents, voice AI, CRM automation, REST APIs, webhooks, and backend engineering**.

---

## Phase 1 — Push-to-Talk Voice Loop ✅

The current implementation covers the complete Phase 1 prototype:

```text
You: 🎙️ "Hi, I want to book an appointment."

System:
  You: Hi, I want to book an appointment.
  AI:  Sure, I'd be happy to help. What day would you prefer?

🔊 Browser speaks the response aloud.
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
┌─────────────────────┐
│ Backend (FastAPI)    │
│ POST /api/chat      │
│ → LLM / Fallback    │
└──────────┬──────────┘
           │ text
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

| Part       | Technology                     | Why                          |
| ---------- | ------------------------------ | ---------------------------- |
| Frontend   | HTML + CSS + JavaScript        | Simple, no framework bloat   |
| Microphone | Web Speech API                 | Built into browser           |
| STT        | Web Speech API                 | Free                         |
| Backend    | FastAPI + Python               | Matches existing skills      |
| AI         | GitHub Models / OpenAI / Echo  | Configurable via `.env`      |
| TTS        | Browser SpeechSynthesis API    | Free                         |
| Hosting    | Localhost                      | $0                           |

### Milestones Implemented

- [x] 1️⃣ Browser microphone capture
- [x] 2️⃣ Speech-to-text transcription in UI
- [x] 3️⃣ FastAPI backend (`POST /api/chat`)
- [x] 4️⃣ LLM integration (with scripted fallback)
- [x] 5️⃣ Text-to-speech response
- [x] 6️⃣ Conversation history/context

---

## Project Structure

```
voice-ai-agent/
│
├── backend/
│   ├── main.py            # FastAPI server + LLM integration
│   ├── requirements.txt   # Python dependencies
│   └── .env               # LLM API keys (gitignored)
│
├── frontend/
│   ├── index.html          # Voice agent UI
│   ├── style.css           # Design system
│   └── script.js           # STT + chat + TTS logic
│
├── .gitignore
└── README.md
```

---

## Quick Start

### 1. Install dependencies

```bash
cd voice-ai-agent
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

pip install -r backend/requirements.txt
```

### 2. (Optional) Configure an LLM

Edit `backend/.env` and uncomment/fill in your keys:

```env
# GitHub Models (free with GitHub Student)
LLM_PROVIDER=github
LLM_API_KEY=your_github_token
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://models.inference.ai.azure.com
```

> **Without an LLM key**, the agent uses a built-in scripted fallback that simulates a sales conversation. The full voice loop still works.

### 3. Run the server

```bash
uvicorn backend.main:app --reload --port 8000
```

### 4. Open in browser

Navigate to **http://localhost:8000** in **Chrome** or **Edge** (required for Web Speech API).

Click the microphone → speak → watch the transcript appear → hear the AI respond.

---

## API Reference

### `GET /health`

Health check. Returns `{ "status": "healthy", "llm_configured": true/false }`.

### `POST /api/chat`

Main chat endpoint.

**Request:**
```json
{
  "message": "I want to book an appointment",
  "history": [
    { "role": "user", "content": "Hi" },
    { "role": "assistant", "content": "Hello! How can I help?" }
  ]
}
```

**Response:**
```json
{
  "reply": "I'd be happy to help you book an appointment! What day works best for you?"
}
```

---

## Future Phases

### Phase 2 — Real-time Voice
- Continuous audio streaming
- WebSocket/WebRTC integration
- Interruption handling & turn detection
- Streaming STT → agent → streaming TTS

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