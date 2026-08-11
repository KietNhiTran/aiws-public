"""
Project Advisor — Chat UI Backend (FastAPI) — OBO Edition

A thin API layer between a browser-based chat UI and Foundry Agent Service.
Follows the Basic Microsoft Foundry Chat reference architecture pattern:
  https://learn.microsoft.com/azure/architecture/ai-ml/architecture/basic-microsoft-foundry-chat

Authentication modes (controlled by AUTH_MODE env var):
  - "obo"  (On-Behalf-Of): Each request uses the logged-in user's identity.
      Easy Auth issues a user token → app exchanges it via OBO for a
      Foundry-scoped token (https://cognitiveservices.azure.com/.default).
      The user must have "Azure AI User" role on the Foundry resource group.
  - "mi"   (Managed Identity — default): Falls back to DefaultAzureCredential.
      Uses system-assigned Managed Identity on App Service, or az login locally.

Prerequisites for OBO mode:
  1. App registration with "Expose an API" → api://<client-id>/user_impersonation
  2. API permissions: Azure Cognitive Services → Delegated → user_impersonation (admin-consented)
  3. Easy Auth loginParameters: scope=openid profile api://<client-id>/user_impersonation
  4. App settings: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
  5. Each user needs "Azure AI User" role on the Foundry resource group

References:
  - OBO flow: https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow
  - Easy Auth: https://learn.microsoft.com/azure/app-service/overview-authentication-authorization
  - MCP OAuth consent: https://learn.microsoft.com/azure/foundry/agents/how-to/mcp-authentication
"""

import os
import json
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from azure.identity import DefaultAzureCredential, OnBehalfOfCredential
from azure.ai.projects import AIProjectClient

load_dotenv(override=False)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT", "")
AGENT_NAME = os.environ.get("AGENT_NAME", "project-advisor")
PORT = int(os.environ.get("PORT", "8000"))

# Auth mode: "obo" for On-Behalf-Of, "mi" for Managed Identity (default)
AUTH_MODE = os.environ.get("AUTH_MODE", "mi").lower()

# OBO-specific config (only needed when AUTH_MODE=obo)
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")

logger = logging.getLogger("chat-ui")

# ---------------------------------------------------------------------------
# Foundry SDK clients
#   - MI mode: singleton created at startup (shared across all requests)
#   - OBO mode: created per-request from the user's Easy Auth token
# ---------------------------------------------------------------------------
_mi_project_client: AIProjectClient | None = None
_mi_openai_client = None


def _get_clients(request: Request | None = None):
    """Return (project_client, openai_client) based on AUTH_MODE.

    OBO mode: extracts the user's access token from Easy Auth header and
    exchanges it for a Foundry-scoped token via OnBehalfOfCredential.

    MI mode: returns the global singleton clients.
    """
    if AUTH_MODE == "obo":
        if request is None:
            raise HTTPException(status_code=500, detail="OBO mode requires a request context")

        # Easy Auth injects the user's AAD access token in this header
        # (requires token store to be enabled on App Service)
        user_token = request.headers.get("x-ms-token-aad-access-token")
        if not user_token:
            raise HTTPException(
                status_code=401,
                detail="No user token found. Is Easy Auth configured with token store enabled?",
            )

        if not all([AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET]):
            raise HTTPException(
                status_code=500,
                detail="OBO mode requires AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET",
            )

        credential = OnBehalfOfCredential(
            tenant_id=AZURE_TENANT_ID,
            client_id=AZURE_CLIENT_ID,
            client_secret=AZURE_CLIENT_SECRET,
            user_assertion=user_token,
        )
        pc = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
        return pc, pc.get_openai_client()

    # MI mode — use the global singleton
    if _mi_openai_client is None:
        raise HTTPException(
            status_code=503,
            detail="Foundry SDK not initialised. Set PROJECT_ENDPOINT in .env",
        )
    return _mi_project_client, _mi_openai_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise SDK clients on startup (MI mode only)."""
    global _mi_project_client, _mi_openai_client

    if not PROJECT_ENDPOINT:
        logger.warning(
            "PROJECT_ENDPOINT not set — the app will start but API calls will fail. "
            "Copy .env.example to .env and set your project endpoint."
        )
    elif AUTH_MODE != "obo":
        _mi_project_client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(),
        )
        _mi_openai_client = _mi_project_client.get_openai_client()
        logger.info("Foundry SDK clients initialised in MI mode (endpoint=%s)", PROJECT_ENDPOINT)
    else:
        logger.info("OBO mode — clients will be created per-request (endpoint=%s)", PROJECT_ENDPOINT)

    yield  # app is running

    logger.info("Shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Project Advisor — Chat UI",
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
        "auth_mode": AUTH_MODE,
        "project_endpoint_configured": bool(PROJECT_ENDPOINT),
    }


# ---------------------------------------------------------------------------
# Conversation management
# ---------------------------------------------------------------------------
@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation(request: Request):
    """Create a new Foundry conversation for multi-turn chat."""
    _, oc = _get_clients(request)
    conversation = oc.conversations.create()
    return ConversationResponse(conversation_id=conversation.id)


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, request: Request):
    """Delete a Foundry conversation and its history."""
    _, oc = _get_clients(request)
    try:
        oc.conversations.delete(conversation_id=conversation_id)
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
async def chat(req: ChatRequest, request: Request):
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
    _, oc = _get_clients(request)

    # Reuse an existing conversation or create a new one
    conversation_id = req.conversation_id
    if not conversation_id:
        conversation = oc.conversations.create()
        conversation_id = conversation.id

    async def event_generator():
        # Tell the client which conversation it belongs to
        yield {
            "event": "conversation_id",
            "data": json.dumps({"conversation_id": conversation_id}),
        }

        try:
            stream = oc.responses.create(
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
async def consent_resume(req: OAuthConsentResume, request: Request):
    """After the user completes OAuth consent in the popup, resume the agent
    response by submitting a new response with previous_response_id."""
    _, oc = _get_clients(request)

    async def event_generator():
        try:
            stream = oc.responses.create(
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
# Debug endpoint — inspect Easy Auth token headers (OBO troubleshooting)
# ---------------------------------------------------------------------------
@app.get("/api/debug-token")
async def debug_token(request: Request):
    """Return Easy Auth headers for debugging. Only useful on App Service."""
    return {
        "auth_mode": AUTH_MODE,
        "has_access_token": bool(request.headers.get("x-ms-token-aad-access-token")),
        "has_id_token": bool(request.headers.get("x-ms-token-aad-id-token")),
        "principal_name": request.headers.get("x-ms-client-principal-name", ""),
        "principal_id": request.headers.get("x-ms-client-principal-id", ""),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True)
