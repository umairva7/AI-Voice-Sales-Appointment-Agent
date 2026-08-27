# AI Voice Sales & Appointment Agent

An end-to-end AI voice agent that can communicate with leads, understand their intent, qualify them, manage CRM data, book appointments, and trigger automated follow-up workflows.

The project is being built as a practical learning project to explore **AI agents, voice AI, CRM automation, REST APIs, webhooks, and backend engineering**.

---

## Project Overview

The goal is to build an AI-powered sales/receptionist agent that can handle the initial interaction with a potential customer and automate the journey from conversation to appointment.

### Example workflow

Lead starts a conversation
        ↓
AI Voice Agent
        ↓
Understands intent
        ↓
Collects lead information
        ↓
Qualifies the lead
        ↓
Calculates lead score
        ↓
Creates/updates CRM contact
        ↓
Books appointment
        ↓
Updates sales pipeline
        ↓
Triggers follow-up automation
        ↓
Human handoff when required

---

## Key Features

### Voice AI

- Voice-based interaction through a browser
- Speech-to-text processing
- AI-generated responses
- Text-to-speech responses
- Conversation context and memory

### AI Agent

- Intent detection
- Lead qualification
- Structured information extraction
- Lead scoring
- Tool calling
- Business rules and system prompts
- Human escalation when required

### CRM Integration

Integration with **GoHighLevel** for:

- Creating contacts
- Updating contacts
- Creating opportunities
- Updating pipeline stages
- Appointment management
- Workflow automation
- Webhook event handling

### Backend

Built with **FastAPI** to handle:

- Agent requests
- CRM API communication
- Webhooks
- Business logic
- Validation
- Error handling
- Database operations

### Automation

The system will automate actions such as:

- Lead qualification
- CRM updates
- Appointment booking
- Appointment reminders
- Follow-up sequences
- Sales notifications
- Human handoff

---

# Architecture

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