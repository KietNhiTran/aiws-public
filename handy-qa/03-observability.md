# Observability, Tracing & Monitoring in Microsoft Foundry V2

> **Workshop coverage:** Module 1 mentions tracing/observability briefly. Module 5 covers basic evaluation. This document goes deep on production monitoring, distributed tracing, continuous evaluation, and the Agent Monitoring Dashboard.

---

## Quick Answer Summary

| Question | Short Answer |
|----------|-------------|
| How do we monitor agents in production? | **Agent Monitoring Dashboard** in Foundry portal — tracks token usage, latency, error rates, and evaluation scores. |
| Do you support OpenTelemetry? | Yes — traces follow [OpenTelemetry semantic conventions for GenAI](https://opentelemetry.io/docs/specs/semconv/gen-ai/). |
| Where do traces go? | **Azure Monitor Application Insights** — connected to your Foundry project. |
| Can we evaluate agents continuously? | Yes — **Continuous evaluation** samples agent responses and scores them against built-in or custom evaluators. |
| What frameworks are supported for tracing? | Foundry SDK, LangChain/LangGraph, OpenAI Agents SDK, Semantic Kernel, Microsoft Agent Framework. |

---

## The Three Pillars of Foundry Observability

```
┌─────────────────────────────────────────────────────────┐
│              Foundry Observability                       │
│                                                         │
│  ┌───────────────┐ ┌──────────────┐ ┌────────────────┐ │
│  │  Evaluation   │ │  Monitoring  │ │   Tracing      │ │
│  │               │ │              │ │                │ │
│  │ • Quality     │ │ • Dashboards │ │ • Distributed  │ │
│  │ • Safety      │ │ • Alerts     │ │   traces       │ │
│  │ • Agent-      │ │ • Token      │ │ • Span-level   │ │
│  │   specific    │ │   usage      │ │   debugging    │ │
│  │ • Custom      │ │ • Latency    │ │ • Conversation │ │
│  │   evaluators  │ │ • Error rate │ │   history      │ │
│  └───────────────┘ └──────────────┘ └────────────────┘ │
│                         │                               │
│                    Azure Monitor                        │
│                 Application Insights                    │
└─────────────────────────────────────────────────────────┘
```

📖 **Reference:** [Observability in generative AI](https://learn.microsoft.com/azure/foundry/concepts/observability)

---

## 1. Setting Up Tracing

### Connect Application Insights to Your Project

1. Open your Foundry project at [ai.azure.com](https://ai.azure.com)
2. In the left navigation, select **Agents**
3. At the top, select **Traces**
4. Select **Connect** → create or connect an Application Insights resource

Alternative path:
1. Select **Project Details** from the project name dropdown
2. Navigate to **Connected resources** → **Add connection**
3. Select **Application Insights**

📖 **Reference:** [Set up tracing in Microsoft Foundry](https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-setup)

### Instrument Code for Tracing

#### Python — Foundry SDK

```bash
pip install azure-ai-projects azure-identity azure-monitor-opentelemetry opentelemetry-sdk
```

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor

# Connect to project
project_client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=os.environ["PROJECT_ENDPOINT"],
)

# Get App Insights connection string and enable telemetry
connection_string = project_client.telemetry.get_application_insights_connection_string()
configure_azure_monitor(connection_string=connection_string)
```

#### Python — LangChain / LangGraph

```bash
pip install langchain-azure-ai langgraph langchain-openai azure-identity
```

```python
from langchain_azure_ai.callbacks.tracers import AzureAIOpenTelemetryTracer

azure_tracer = AzureAIOpenTelemetryTracer(
    connection_string=os.environ["APPLICATION_INSIGHTS_CONNECTION_STRING"],
    enable_content_recording=True,
    name="CIMIC Agent",
)

# Attach to chains/agents
config = {"callbacks": [azure_tracer]}
```

#### Python — OpenAI Agents SDK

```bash
pip install opentelemetry-sdk opentelemetry-instrumentation-openai-agents azure-monitor-opentelemetry-exporter
```

#### Local Debugging (Aspire Dashboard)

```bash
pip install azure-core-tracing-opentelemetry opentelemetry-exporter-otlp opentelemetry-sdk
```

Use [Aspire Dashboard](https://aspiredashboard.com) as a local OTLP-compatible viewer for development.

📖 **Reference:** [Add client-side tracing to Foundry agents](https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-client-side)

### Enable Content Recording

To trace the content of chat messages (may contain personal data):

```python
import os
os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "true"
```

---

## 2. Viewing Traces

### In the Foundry Portal

1. Open your project → **Traces** tab (under Agents)
2. Search, filter, or sort traces from the last 90 days
3. Select a trace to step through each span
4. View **Conversation** results — persistent end-to-end dialogue history

Conversation details include:
- Conversation history
- Response information and token counts
- Ordered actions, run steps, and tool calls
- Inputs and outputs between user and agent

### In Azure Monitor

1. Open Application Insights resource in Azure Portal
2. Select **Agents (Preview)** in the navigation menu
3. Investigate traces via:
   - **View Traces with Agent Runs** — all executions
   - **View Traces with Gen AI Errors** — failed runs
   - Individual tool call or model in **Tool Calls** / **Models** tiles
4. Use **End-to-end transaction details** with the new **Simple View** for story-like trace navigation

📖 **Reference:** [Monitor AI agents with Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/agents-view)

---

## 3. Agent Monitoring Dashboard

The dashboard is the central place for production monitoring in Foundry.

### What It Shows

| Metric Category | Metrics |
|----------------|---------|
| **Operational** | Token consumption, latency, success/error rates |
| **Evaluation** | Quality scores, safety scores from continuous evaluation |
| **Security** | Red team scan results, adversarial test outcomes |

### Configure Settings

Access via the gear icon on the **Monitor** tab:

| Setting | Purpose |
|---------|---------|
| **Continuous evaluation** | Runs evaluations on sampled agent responses (configurable sample rate) |
| **Scheduled evaluations** (preview) | Validates performance against benchmarks on a schedule |
| **Red team scans** (preview) | Adversarial tests to detect data leakage or prohibited actions |
| **Alerts** (preview) | Anomaly detection for latency, token usage, evaluation scores |

📖 **Reference:** [Monitor agents with the Agent Monitoring Dashboard](https://learn.microsoft.com/azure/foundry/observability/how-to/how-to-monitor-agents-dashboard)

---

## 4. Continuous Evaluation

Runs near-real-time evaluations on sampled agent responses in production.

### Built-in Evaluators

| Category | Evaluators |
|----------|-----------|
| **General quality** | Coherence, fluency, relevance |
| **RAG-specific** | Groundedness, retrieval relevance |
| **Safety** | Hate/unfairness, violence, self-harm, protected materials |
| **Agent-specific** | Intent resolution, task adherence, tool call accuracy |

### Setup via Python SDK

```bash
pip install "azure-ai-projects>=2.0.0" python-dotenv
```

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
)

# Create continuous evaluation rule
# (runs when agent response completes)
```

### Permissions Required
- Project managed identity needs **Azure AI User** role
- User needs access to Application Insights and Log Analytics workspace
- For log-based views: **Log Analytics Reader** role

📖 **Reference:** [Set up continuous evaluation](https://learn.microsoft.com/azure/foundry/observability/how-to/how-to-monitor-agents-dashboard#set-up-continuous-evaluation)

---

## 5. Monitoring Custom / External Agents

Foundry can monitor agents that don't run on the platform:

1. **Onboard** your custom agent via [Register and manage custom agents](https://learn.microsoft.com/azure/foundry/control-plane/register-custom-agent)
2. **Instrument** the agent to comply with OpenTelemetry semantic conventions for GenAI
3. **Configure** the agent to send telemetry to the same Application Insights instance
4. **View** metrics in Foundry Control Plane → Asset page → Monitor tab

---

## Q&A

1. **"How do we know if the agent is giving good answers in production?"** → Continuous evaluation samples responses and scores them against quality/safety evaluators. Results show in the Monitoring Dashboard.

2. **"Can we set up alerts?"** → Yes (preview). Configure alerts for latency spikes, token usage anomalies, evaluation score drops, or red team findings.

3. **"What if we're using LangChain / Semantic Kernel?"** → Foundry supports tracing for all major frameworks via OpenTelemetry. LangChain has a dedicated `langchain-azure-ai` tracer. Semantic Kernel has built-in OTel support.

4. **"How long are traces retained?"** → 90 days in the Foundry portal. Application Insights retention is configurable (default 90 days, up to 730 days).

5. **"Can we integrate with our existing Azure Monitor setup?"** → Yes. Foundry traces go to Application Insights, which is part of Azure Monitor. You can use existing dashboards, workbooks, and alerting.

6. **"What about CI/CD integration?"** → Evaluation can be integrated into pipelines via [GitHub Actions](https://learn.microsoft.com/azure/foundry/how-to/evaluation-github-action) or [Azure DevOps](https://learn.microsoft.com/azure/foundry/how-to/evaluation-azure-devops).


