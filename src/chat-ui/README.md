# Project Advisor — Chat UI

A browser-based chat interface that demonstrates how a **frontend client consumes a Foundry Agent Service agent**. This follows the [Basic Microsoft Foundry Chat reference architecture](https://learn.microsoft.com/azure/architecture/ai-ml/architecture/basic-microsoft-foundry-chat) pattern.

## Architecture

```
┌──────────────────┐        SSE (streaming)        ┌──────────────────────┐
│  Browser Chat UI │  ───── POST /api/chat ──────▶  │  FastAPI Backend     │
│  (HTML/CSS/JS)   │  ◀──── Server-Sent Events ──── │  (Python + Uvicorn)  │
└──────────────────┘                                └──────────┬───────────┘
                                                               │
                                              DefaultAzureCredential
                                                               │
                                                    ┌──────────▼───────────┐
                                                    │  Foundry Agent       │
                                                    │  Service             │
                                                    │  (project-advisor    │
                                                    │   agent)             │
                                                    └──────────────────────┘
```

**Key design decisions** (aligned with Microsoft best practices):

| Decision | Rationale |
|---|---|
| Backend proxies all Foundry SDK calls | No Azure credentials in the browser; uses `DefaultAzureCredential` |
| Server-Sent Events (SSE) for streaming | Real-time token-by-token response; same pattern as the [Customer Chatbot accelerator](https://aka.ms/CSAGoldStandards/CustomerChatbot) |
| Multi-turn conversations | Uses Foundry `conversations.create()` to maintain context across turns |
| Static files served by FastAPI | Single deployment unit — easy to host on Azure App Service |
| Vanilla HTML/CSS/JS frontend | Zero build step; no Node.js/npm required for the workshop |

## Prerequisites

- Python 3.10+
- Azure CLI logged in (`az login`) for `DefaultAzureCredential`
- A **published** Foundry agent (created via Module 2 or `src/foundry-agent/agent.py`)
- The agent name (default: `project-advisor`)

## Quick Start

```bash
# 1. Navigate to this directory
cd src/chat-ui

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
# Edit .env and set your PROJECT_ENDPOINT

# 5. Run the app
python app.py
```

Then open **http://localhost:8000** in your browser.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves the chat UI |
| `GET` | `/api/health` | Health check — shows agent config status |
| `POST` | `/api/conversations` | Create a new Foundry conversation |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation |
| `POST` | `/api/chat` | Send a message; returns SSE stream |

### SSE Event Types (from `/api/chat`)

| Event | Payload | Description |
|---|---|---|
| `conversation_id` | `{ "conversation_id": "..." }` | Sent once at stream start |
| `delta` | `{ "text": "..." }` | A text token from the agent |
| `done` | `{ "status": "complete" }` | Stream finished |
| `error` | `{ "error": "..." }` | Error message |

## Project Structure

```
src/chat-ui/
├── app.py                # FastAPI backend — proxies chat to Foundry Agent Service
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── README.md             # This file
└── static/
    ├── index.html        # Chat UI page
    ├── styles.css        # Chat UI styling
    └── chat.js           # Client-side chat logic + SSE handling
2. **Backend creates/reuses a Foundry conversation** → calls `openai.responses.create(stream=True)` with the agent reference.
3. **Tokens stream back via SSE** → each delta event is rendered in the chat bubble in real-time.
4. **Multi-turn context is preserved** → the same `conversation_id` is reused for follow-up messages.

## References

- [Basic Microsoft Foundry Chat — Architecture](https://learn.microsoft.com/azure/architecture/ai-ml/architecture/basic-microsoft-foundry-chat)
- [Foundry Agent Service — Streaming](https://learn.microsoft.com/azure/foundry/agents/concepts/runtime-components#streaming-and-background-responses)
- [Customer Chatbot Accelerator](https://aka.ms/CSAGoldStandards/CustomerChatbot) — Python + React reference
- [Chat with your Data Accelerator](https://aka.ms/CSAGoldStandards/ChatWithYourData) — full RAG pattern
- [Multi-Agent Automation Engine](https://aka.ms/CSAGoldStandards/MultiAgent) — advanced orchestration
