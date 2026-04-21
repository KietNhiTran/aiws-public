"""
CIMIC Project Advisor — Chat UI Backend (FastAPI)

A thin API layer between a browser-based chat UI and Foundry Agent Service.
Follows the Basic Microsoft Foundry Chat reference architecture pattern:
  https://learn.microsoft.com/azure/architecture/ai-ml/architecture/basic-microsoft-foundry-chat

The backend:
  1. Authenticates to Azure using DefaultAzureCredential (no secrets in the frontend)
  2. Manages Foundry conversations (create / list / delete)
  3. Proxies chat messages to the Foundry agent and streams responses back via SSE
"""

import os
import json
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv(override=False)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT", "")
AGENT_NAME = os.environ.get("AGENT_NAME", "cimic-project-advisor")
PORT = int(os.environ.get("PORT", "8000"))

logger = logging.getLogger("chat-ui")

# ---------------------------------------------------------------------------
# Foundry SDK clients (initialised once at startup)
# ---------------------------------------------------------------------------
project_client: AIProjectClient | None = None
openai_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise SDK clients on startup."""
    global project_client, openai_client

    if not PROJECT_ENDPOINT:
        logger.warning(
            "PROJECT_ENDPOINT not set — the app will start but API calls will fail. "
            "Copy .env.example to .env and set your project endpoint."
        )
    else:
        project_client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(),
        )
        openai_client = project_client.get_openai_client()
        logger.info("Foundry SDK clients initialised (endpoint=%s)", PROJECT_ENDPOINT)

    yield  # app is running

    logger.info("Shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CIMIC Project Advisor — Chat UI",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ConversationResponse(BaseModel):
    conversation_id: str


class OAuthConsentResume(BaseModel):
    """Resume agent response after user completes OAuth consent."""
    conversation_id: str
    previous_response_id: str
    user_message: str


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "agent_name": AGENT_NAME,
        "project_endpoint_configured": bool(PROJECT_ENDPOINT),
    }


# ---------------------------------------------------------------------------
# Conversation management
# ---------------------------------------------------------------------------
@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation():
    """Create a new Foundry conversation for multi-turn chat."""
    _check_client()
    conversation = openai_client.conversations.create()
    return ConversationResponse(conversation_id=conversation.id)


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a Foundry conversation and its history."""
    _check_client()
    try:
        openai_client.conversations.delete(conversation_id=conversation_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Stream event helpers
# ---------------------------------------------------------------------------
_AUTH_KEYWORDS = {"unauthorized", "401", "403", "token expired", "authentication",
                  "forbidden", "invalid token", "token is expired"}


def _is_auth_error(msg: str) -> bool:
    lower = msg.lower()
    return any(kw in lower for kw in _AUTH_KEYWORDS)


def _iter_stream_events(stream):
    """Process a Foundry response stream and yield SSE-formatted dicts.

    Handles:
      - text deltas
      - oauth_consent_request  (OAuth identity passthrough — user must consent)
      - mcp_approval_request   (tool-call approval)

    Reference:
      https://learn.microsoft.com/azure/foundry/agents/how-to/mcp-authentication
    """
    last_response_id = None

    for event in stream:
        event_type = getattr(event, "type", "")
        logger.debug("Stream event: %s", event_type)

        # ── Text deltas ──────────────────────────────────────────────
        if hasattr(event, "delta") and event.delta:
            yield {
                "event": "delta",
                "data": json.dumps({"text": event.delta}),
            }

        # ── Output-item level events ─────────────────────────────────
        item = getattr(event, "item", None)
        if item:
            item_type = getattr(item, "type", None)

            # OAuth consent request (identity passthrough)
            # Docs: item.type == "oauth_consent_request", item.consent_link, item.id
            if item_type == "oauth_consent_request":
                consent_link = getattr(item, "consent_link", "")
                server_label = getattr(item, "server_label", "MCP Tool")
                item_id = getattr(item, "id", "")
                logger.info("OAuth consent request (server=%s, id=%s)", server_label, item_id)
                yield {
                    "event": "auth_required",
                    "data": json.dumps({
                        "consent_link": consent_link,
                        "server_label": server_label,
                        "response_id": last_response_id or "",
                    }),
                }

            # MCP tool-call approval request
            if item_type == "mcp_approval_request":
                logger.info("MCP approval request (server=%s)",
                            getattr(item, "server_label", "unknown"))
                yield {
                    "event": "mcp_approval",
                    "data": json.dumps({
                        "approval_request_id": getattr(item, "id", ""),
                        "server_label": getattr(item, "server_label", "MCP Tool"),
                        "name": getattr(item, "name", ""),
                    }),
                }

        # ── Response-level completion event ──────────────────────────
        resp_obj = getattr(event, "response", None)
        if resp_obj:
            last_response_id = getattr(resp_obj, "id", last_response_id)
            for out_item in getattr(resp_obj, "output", None) or []:
                out_type = getattr(out_item, "type", None)
                if out_type == "oauth_consent_request":
                    consent_link = getattr(out_item, "consent_link", "")
                    server_label = getattr(out_item, "server_label", "MCP Tool")
                    logger.info("OAuth consent in response output (server=%s)", server_label)
                    yield {
                        "event": "auth_required",
                        "data": json.dumps({
                            "consent_link": consent_link,
                            "server_label": server_label,
                            "response_id": last_response_id or "",
                        }),
                    }

    # After stream ends, emit the response_id so the frontend can use it
    if last_response_id:
        yield {
            "event": "response_id",
            "data": json.dumps({"response_id": last_response_id}),
        }


# ---------------------------------------------------------------------------
# Chat — streaming via SSE
# ---------------------------------------------------------------------------
@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    Send a user message to the Foundry agent and stream the response back
    as Server-Sent Events (SSE).

    SSE event types:
      - conversation_id  : the conversation ID (sent once at the start)
      - response_id      : the Foundry response ID (sent at stream end)
      - delta             : a text token from the agent
      - auth_required     : MCP tool needs user OAuth consent (consent_link)
      - mcp_approval      : MCP tool-call approval request
      - auth_error        : authentication-related failure
      - done              : signals the stream is complete
      - error             : a non-auth error message
    """
    _check_client()

    # Reuse an existing conversation or create a new one
    conversation_id = req.conversation_id
    if not conversation_id:
        conversation = openai_client.conversations.create()
        conversation_id = conversation.id

    async def event_generator():
        # Tell the client which conversation it belongs to
        yield {
            "event": "conversation_id",
            "data": json.dumps({"conversation_id": conversation_id}),
        }

        try:
            stream = openai_client.responses.create(
                conversation=conversation_id,
                input=req.message,
                stream=True,
                extra_body={
                    "agent_reference": {
                        "name": AGENT_NAME,
                        "type": "agent_reference",
                    }
                },
            )

            for sse_event in _iter_stream_events(stream):
                yield sse_event

            yield {"event": "done", "data": json.dumps({"status": "complete"})}

        except Exception as exc:
            logger.exception("Error during agent streaming")
            error_msg = str(exc)
            if _is_auth_error(error_msg):
                yield {
                    "event": "auth_error",
                    "data": json.dumps({"error": error_msg}),
                }
            else:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": error_msg}),
                }

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# OAuth consent resume — re-submit after user completed consent popup
# Reference: https://learn.microsoft.com/azure/foundry/agents/how-to/mcp-authentication
# ---------------------------------------------------------------------------
@app.post("/api/chat/consent-resume")
async def consent_resume(req: OAuthConsentResume):
    """After the user completes OAuth consent in the popup, resume the agent
    response by submitting a new response with previous_response_id."""
    _check_client()

    async def event_generator():
        try:
            stream = openai_client.responses.create(
                previous_response_id=req.previous_response_id,
                input=req.user_message,
                stream=True,
                extra_body={
                    "agent_reference": {
                        "name": AGENT_NAME,
                        "type": "agent_reference",
                    },
                    "tool_choice": "required",
                },
            )

            for sse_event in _iter_stream_events(stream):
                yield sse_event

            yield {"event": "done", "data": json.dumps({"status": "complete"})}

        except Exception as exc:
            logger.exception("Error during consent-resume streaming")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(exc)}),
            }

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Static files — serve the chat frontend
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _check_client():
    if openai_client is None:
        raise HTTPException(
            status_code=503,
            detail="Foundry SDK not initialised. Set PROJECT_ENDPOINT in .env",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)
