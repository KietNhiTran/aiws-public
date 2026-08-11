# Project Advisor — Chat UI (OBO Edition)

A browser-based chat interface for a published Microsoft Foundry agent. This edition supports per-request **On-Behalf-Of (OBO)** authentication through Azure App Service Easy Auth, with Managed Identity available as a fallback mode.

## Architecture

```text
Browser user
    │
    │ Easy Auth sign-in
    ▼
Azure App Service / FastAPI
    │
    │ OBO: user token exchanged for a Foundry-scoped token
    │ MI:  DefaultAzureCredential
    ▼
Microsoft Foundry Agent Service
    │
    │ Authentication configured separately on each tool connection
    ▼
MCP server / connected tool
```

The browser sends chat requests to FastAPI and receives streamed Server-Sent Events (SSE). Azure credentials and client secrets are never sent to browser JavaScript.

## Authentication Modes

Set `AUTH_MODE` in `.env` or the App Service application settings.

| Mode | Foundry caller identity | Intended use |
|---|---|---|
| `obo` | Signed-in user, through `OnBehalfOfCredential` | Interactive App Service deployment with per-user Foundry access |
| `mi` | App Service managed identity, or the local Azure CLI identity | Local development and non-interactive application access |

### OBO Flow

When `AUTH_MODE=obo`:

1. App Service Easy Auth signs in the user and stores their token.
2. Easy Auth injects the token into `x-ms-token-aad-access-token`.
3. FastAPI creates an `OnBehalfOfCredential` using that token as the user assertion.
4. The Azure SDK requests a Foundry-scoped delegated token.
5. A per-request `AIProjectClient` invokes the published agent as the signed-in user.

Each user must have the **Azure AI User** role on the Foundry resource group or project scope.

### MCP and Tool Identity

OBO authentication to Foundry does **not** automatically determine the identity used by an MCP server or another connected tool. Tool authentication is configured on the published agent in Foundry:

| Tool authentication | Downstream identity |
|---|---|
| OAuth Identity Passthrough | Signed-in user; supports per-user Databricks permissions and row-level security |
| Microsoft Entra - Agent Identity | Foundry-managed identity dedicated to the agent |
| Microsoft Entra - Project Managed Identity | Managed identity shared by agents in the project |

This UI handles `oauth_consent_request` events when an MCP connection uses OAuth Identity Passthrough. It opens the Foundry consent link and resumes the response after authorization. Agent Identity and Project Managed Identity do not require that browser consent flow.

Check the effective MCP setting in **Foundry portal → Agent → Tools → Genie MCP → Authentication**.

## Prerequisites

Common requirements:

- Python 3.10+
- A published Foundry agent
- The Foundry project endpoint and published agent name

Additional OBO requirements:

- An Entra ID app registration with `api://<client-id>/user_impersonation` exposed
- Delegated Azure Cognitive Services `user_impersonation` permission with admin consent
- App Service Easy Auth configured with the token store enabled
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET` application settings
- Each interactive user assigned the required Foundry RBAC role

The supplied `auth-config.json` contains the expected Easy Auth structure. Replace tenant- and application-specific values before applying it to another environment.

## Local Quick Start

Easy Auth headers are only injected by App Service. For local development, use `AUTH_MODE=mi` and authenticate with Azure CLI:

```powershell
Set-Location src/chat-ui-obo

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
# Edit .env: set PROJECT_ENDPOINT, AGENT_NAME, and AUTH_MODE=mi

az login
python app.py
```

Open `http://localhost:8000`.

Running locally with `AUTH_MODE=obo` returns HTTP 401 because the local server does not receive the Easy Auth token header.

## App Service OBO Configuration

Configure these application settings without committing secret values:

```text
PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
AGENT_NAME=<published-agent-name>
AUTH_MODE=obo
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<app-registration-client-id>
AZURE_CLIENT_SECRET=<app-registration-client-secret>
```

Enable App Service Authentication with Microsoft Entra ID and enable its token store. The login scope must include:

```text
openid profile api://<client-id>/user_impersonation
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves the chat UI |
| `GET` | `/api/health` | Reports the agent, authentication mode, and endpoint status |
| `GET` | `/api/debug-token` | Reports whether Easy Auth headers are present; does not return token values |
| `POST` | `/api/conversations` | Creates a Foundry conversation |
| `DELETE` | `/api/conversations/{id}` | Deletes a Foundry conversation |
| `POST` | `/api/chat` | Sends a message and returns an SSE stream |
| `POST` | `/api/chat/consent-resume` | Resumes an MCP call after user OAuth consent |

### SSE Event Types

| Event | Description |
|---|---|
| `conversation_id` | Foundry conversation identifier |
| `response_id` | Foundry response identifier used by consent resume |
| `delta` | Streamed text from the agent |
| `auth_required` | MCP OAuth consent is required; includes the consent link |
| `mcp_approval` | An MCP tool call requires approval |
| `auth_error` | Foundry or connected-tool authentication failed |
| `error` | A non-authentication request error occurred |
| `done` | The stream completed |

## Project Structure

```text
src/chat-ui-obo/
├── app.py                # FastAPI backend, OBO exchange, and Foundry streaming
├── auth-config.json      # App Service Easy Auth configuration template
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── README.md             # This file
└── static/
    ├── index.html        # Chat interface
    ├── styles.css        # UI styling
    └── chat.js           # SSE handling and MCP OAuth consent UI
```

## Request Flow

1. The browser posts a message and optional conversation ID to `/api/chat`.
2. `_get_clients()` selects OBO or Managed Identity authentication.
3. The backend creates or reuses a Foundry conversation.
4. `responses.create()` invokes the published agent by `AGENT_NAME`.
5. Text, approval, and authentication events stream to the browser over SSE.
6. If an MCP server requests OAuth consent, the browser opens the supplied consent link.
7. The browser calls `/api/chat/consent-resume` to continue the tool invocation.

## References

- [Basic Microsoft Foundry Chat architecture](https://learn.microsoft.com/azure/architecture/ai-ml/architecture/basic-microsoft-foundry-chat)
- [Microsoft identity platform OBO flow](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow)
- [App Service authentication and authorization](https://learn.microsoft.com/azure/app-service/overview-authentication-authorization)
- [Foundry MCP server authentication](https://learn.microsoft.com/azure/foundry/agents/how-to/mcp-authentication)
- [Foundry Agent Service runtime components](https://learn.microsoft.com/azure/foundry/agents/concepts/runtime-components)
