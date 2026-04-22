# Module 1: Microsoft Foundry Overview & Setup

**Duration:** 80 minutes (Hands-On) / 40 minutes (Led Demo)  
**Objective:** Understand what Microsoft Foundry is, why AI agents matter for infrastructure operations, and how the platform handles enterprise governance — then provision a Foundry resource and project, deploy a foundation model, and configure the environment for agent development.

---

## Part A — Foundry Overview (~30 min)

### 1.1 What is Microsoft Foundry?

Microsoft Foundry (the current name — formerly Azure AI Foundry / Azure AI Studio) is Microsoft's unified platform for building, deploying, and managing AI applications. It brings together models, tools, data connectors, and governance under a single portal at [ai.azure.com](https://ai.azure.com).

#### Key Capabilities

| Capability | What It Does | Industry Example |
|-----------|-------------|-------------------|
| **Model Catalog** | Access 1,900+ models — OpenAI, Meta, Mistral, Cohere, and more | Deploy GPT-4o for agent reasoning |
| **Agent Service** | Low-code and pro-code agent development with built-in tool orchestration | Build the Project Intelligence Agent |
| **Tool Ecosystem** | Built-in tools (File Search, Code Interpreter, Web Search) + MCP server connections | Connect to Databricks data, policy documents, market intelligence |
| **Evaluation** | Batch evaluation with LLM-as-judge, built-in quality and safety evaluators | Score agent responses for relevance, accuracy, and safety |
| **Tracing & Observability** | End-to-end trace logging via Azure Monitor and Application Insights | Monitor agent conversations, tool calls, and latency |
| **Responsible AI** | Content safety filters, prompt shields, groundedness detection | Ensure agent outputs meet compliance standards |

#### Where Foundry Fits in the Microsoft AI Stack

```
┌─────────────────────────────────────────────────────┐
│                   Microsoft Foundry                  │
│   (Build, deploy, manage AI agents & applications)  │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │  Model    │  │  Agent   │  │   Evaluation &    │  │
│  │  Catalog  │  │  Service │  │   Responsible AI  │  │
│  └────┬─────┘  └────┬─────┘  └───────────────────┘  │
└───────┼─────────────┼────────────────────────────────┘
        │             │
  ┌─────▼─────┐  ┌────▼──────────────────────────────┐
  │  Azure    │  │           Tool Connections         │
  │  OpenAI   │  │  MCP Servers, File Search, Bing,  │
  │  Service  │  │  Code Interpreter, Custom APIs     │
  └───────────┘  └───────────────────────────────────┘
```

Foundry provides a secure, enterprise-grade platform to build AI agents that can access operational data across construction and services divisions.

---

### 1.2 Why AI Agents for Infrastructure Operations?

Traditional BI dashboards and reports require users to know *what* to ask and *where* to look. AI agents flip this — a project manager describes what they need in natural language, and the agent figures out which data sources to query, what calculations to run, and how to present the answer.

#### Chatbot vs. Agent

| | Traditional Chatbot | AI Agent |
|---|---|---|
| **Data access** | Pre-scripted FAQ responses | Queries live databases, documents, and web in real-time |
| **Reasoning** | Pattern matching / keyword routing | Multi-step reasoning — decides which tools to call and in what order |
| **Calculations** | None (or pre-built) | Generates and executes code for EVM, trend analysis, what-if scenarios |
| **Context** | Single data source | Synthesises across multiple sources in one response |
| **Example** | "What is our safety policy?" → returns a link | "Compare our Northern Basin safety record against the Zero Harm targets and show a trend chart" → queries incidents, retrieves policy, generates chart |

#### Construction Industry Use Cases

| Use Case | Who Benefits | What the Agent Does |
|----------|-------------|-------------------|
| **Executive Portfolio Review** | C-suite, Program Directors | Summarises RAG status, total budget vs actuals, and open risks across all projects |
| **Site Visit Briefing** | Project Managers | Pulls financials, equipment health, safety incidents, and weather for a specific site into one briefing |
| **Predictive Maintenance** | Equipment/Fleet Managers | Identifies at-risk equipment by correlating operating hours, engine temp, and maintenance history |
| **Safety Trend Analysis** | HSE Officers | Charts incident trends by division, identifies root causes, compares against Zero Harm targets |
| **Procurement Intelligence** | Supply Chain Teams | Compares internal pricing with live market rates; flags supply risks and price increases |
| **Cost Estimation** | Quantity Surveyors | Calculates material costs using internal pricing + current market data, with sensitivity analysis |

> **Key insight:** A single agent with the right tools replaces multiple dashboards, spreadsheets, and manual report compilation. The value isn't just speed — it's the ability to *combine* data from different systems that were previously siloed.

---

### 1.3 AI Agents — Key Concepts

An **AI agent** is more than a chatbot. It can reason about a user's request, decide which tools to call, retrieve data, perform calculations, and synthesise a response — all autonomously.

#### The Agent Loop

```
User Query → Agent (LLM) → Reason → Select Tool(s) → Execute → Synthesise → Response
                  ↑                                        │
                  └────────────── iterate if needed ───────┘
```

| Concept | Description |
|---------|-------------|
| **System Prompt** | Instructions that define the agent's persona, knowledge scope, and response rules |
| **Tools** | Capabilities the agent can invoke — data queries, document search, calculations, web search |
| **Grounding** | Connecting the agent to real data so it doesn't rely solely on training knowledge |
| **MCP (Model Context Protocol)** | An open standard for connecting AI agents to external data sources and tools — Databricks, GitHub, and others expose MCP endpoints |
| **Orchestration** | The agent decides which tool(s) to call, in what order, and how to combine results |

#### Tools We'll Use in This Workshop

| Tool | Type | Purpose |
|------|------|---------|
| **File Search** | Built-in | Search uploaded documents (company policies, governance frameworks) |
| **Code Interpreter** | Built-in | Run Python code for calculations, charts, data analysis |
| **Web Search** | Built-in | Retrieve live web data (market prices, news, weather) |
| **Databricks Genie MCP** | MCP Server | Query structured data in Databricks via natural language → SQL |

---

### 1.4 Workshop Architecture

This is building towards the **Project Intelligence Agent** — a single agent wired to all four tools:

```
┌──────────────────────────────────────────────────────────────────┐
│                  Project Intelligence Agent                      │
│                                                                  │
│  System Prompt: Project Advisor persona                          │
│  Model: GPT-4o                                                   │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐   │
│  │    File       │ │    Code      │ │     Web Search          │   │
│  │   Search      │ │  Interpreter │ │                        │   │
│  │ (policies,    │ │ (calcs,      │ │ (market prices,        │   │
│  │  governance)  │ │  charts)     │ │  industry news)        │   │
│  └──────────────┘ └──────────────┘ └────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  Databricks Genie MCP                                   │     │
│  │  Natural Language → SQL across 4 workshop datasets      │     │
│  │  (financials, equipment, safety, procurement)           │     │
│  └─────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
```

Each module builds one piece:

| Module | What You Build | Tool Added |
|--------|---------------|------------|
| **1** (this module) | Foundry resource, project, model deployment | — (foundation) |
| **2** | Agent + system prompt | File Search, Code Interpreter |
| **3** | Databricks data connection | Genie MCP |
| **4** | Web grounding + concepts | Web Search |
| **5** | Wire everything together, test, evaluate | All 4 tools combined |

---

### 1.5 Agent Development Approaches

Foundry supports two paths for building agents. This workshop uses the **low-code** approach — everything is done in the portal. The pro-code path is available for teams that need CI/CD pipelines, custom orchestration, or programmatic control.

| | Low-Code (Portal) | Pro-Code (SDK) |
|---|---|---|
| **Interface** | Foundry Portal at ai.azure.com | Python SDK (`azure-ai-projects`) |
| **Agent creation** | Click-through wizard | `client.agents.create_agent()` |
| **System prompt** | Text editor in portal | String in code |
| **Tool connection** | Search and connect via UI | Programmatic tool definitions |
| **Testing** | Built-in playground chat | Script-based conversation loops |
| **Evaluation** | Portal evaluation wizard | `client.evaluations.create()` |
| **Best for** | Prototyping, workshops, business users | Production pipelines, version control, automated testing |
| **This workshop** | ✅ Modules 1–5 | Shown in Module 5 evaluation (SDK snippet) |

> **Note:** Agents built in the portal and via SDK are fully interchangeable — you can create an agent in the portal, then manage it via SDK, or vice versa. The underlying API is the same.

---

### 1.6 Enterprise Governance & Security

A key reason to use Foundry (rather than calling OpenAI APIs directly) is the enterprise governance layer. For an organisation with sensitive financial, safety, and operational data, this matters.

| Governance Layer | What Foundry Provides |
|-----------------|-----------------------|
| **Identity & Access** | Microsoft Entra ID authentication; RBAC at resource and project scope (`Azure AI User`, `Azure AI Owner`) |
| **Network Isolation** | Private endpoints, managed virtual networks, no public internet exposure for production |
| **Data Residency** | Deploy in Australia East — data stays in-region |
| **Content Safety** | Built-in filters for harmful content; prompt shields against injection attacks |
| **Tracing & Audit** | Every agent conversation, tool call, and model invocation is logged to Azure Monitor / Application Insights |
| **Model Governance** | Centrally manage which models are deployed, token quotas, and cost controls at the Foundry resource level |
| **Tool-Level Security** | Databricks Genie uses OAuth passthrough — each user's query runs under their own Databricks permissions (Unity Catalog row-level security) |

```
┌─────────────────────────────────────────────────────────┐
│                   Foundry Resource                       │
│         (IT/Admin: governance, networking, models)       │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │              Foundry Project                      │    │
│  │     (Developer: agents, evals, files, traces)     │    │
│  │                                                    │    │
│  │  Agent ──► Tool ──► External System               │    │
│  │            │         (Databricks, Bing, etc.)     │    │
│  │            │                                       │    │
│  │            ▼                                       │    │
│  │  Content Safety Filters                           │    │
│  │  Tracing & Audit Logs                             │    │
│  │  RBAC (per-user permissions)                      │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

> **How It Applies:** The combination of Entra ID + Unity Catalog means a Contoso Mining user querying the agent only sees Contoso Mining data, while a Contoso Build user sees Contoso Build data — all through the same agent, with no code changes required.

---

## Part B — Foundry Setup

### 1.7 V2 Resource Model (No More Hub)

> **Important:** The previous "Hub + Project" model (Azure AI Hub) is **deprecated** since June 2025. The new architecture uses a flat **Foundry resource → Project** hierarchy. Do **not** create a Hub resource for new work.

| Concept | Old (Hub-based, deprecated) | New (Foundry V2, current) |
|---------|---------------------------|--------------------------|
| Top-level resource | Azure AI Hub | **Foundry resource** (`Microsoft.CognitiveServices/account`, kind `AIServices`) |
| Development workspace | Hub-based project | **Foundry project** (child resource of Foundry resource) |
| Shared infrastructure | Hub managed Storage, Key Vault, etc. | Foundry resource manages governance; optional BYOS (Bring Your Own Storage) |
| Portal | `ai.azure.com` (classic toggle) | `ai.azure.com` (New Foundry toggle **ON**) |

---

### 1.8 Create a Foundry Resource & Project

### Step 1: Navigate to Microsoft Foundry Portal

1. Open [https://ai.azure.com](https://ai.azure.com)
2. Sign in with your Azure credentials
3. Ensure the **New Foundry** toggle is **ON** (upper-right area). This enables the V2 experience.

### Step 2: Create a New Project

When you create a project, the portal **automatically provisions a Foundry resource** for you (if one doesn't already exist).

1. The project you're working on appears in the **upper-left corner**
2. Click the **project name** → select **Create new project**
3. Enter the project name: `project-intelligence`
4. Click **Create project** — or expand **Advanced options** for more control

### Step 3: Advanced Options (Recommended)

Expand the advanced options to customise:

| Field | Value |
|-------|-------|
| Project name | `project-intelligence` |
| Resource group | `rg-ai-workshop` (create new) |
| Location | *Select the region closest to your location* |

> **Tip:** Create a new resource group specifically for the workshop. This makes cleanup easy — delete the resource group to remove all resources at once.

Click **Create**. The portal provisions:
- A **Foundry resource** (top-level Azure resource for governance, model deployments, networking)
- A **Foundry project** (child resource where you build agents, evaluations, and files)

### Step 4: Note Your Project Endpoint

On the project **Home** page, you will see the **project endpoint** and **API key**. Copy the endpoint — you will need this later:

```
https://<foundry-resource-name>.ai.azure.com/api/projects/project-intelligence
```

> **Note:** You don't need the API key if you use **Microsoft Entra ID** authentication (recommended).

---

### 1.9 Understanding the V2 Resource Hierarchy

```
Foundry Resource (top-level — governance, networking, model deployments)
│
├── Project: project-intelligence (default)
│     ├── Agents
│     ├── Evaluations
│     ├── Files & Datasets
│     └── Tracing
│
└── (Optional) Additional projects for other teams/use cases
```

**Key concepts:**
- **Foundry resource** — IT/admin scope: manages security, networking, model deployments, connections, and cost
- **Project** — Developer scope: organises agents, evaluations, files, and tracing for a specific use case
- **Default project** — The first project created becomes the "default" project with the broadest feature support
- **RBAC inheritance** — Projects inherit access controls from the parent Foundry resource, but can also have project-scoped assignments

---

### 1.10 Deploy a Foundation Model

The agent requires a language model to power its reasoning. We'll deploy **GPT-4o**.

### Step 1: Open Model Catalog

1. In your project, navigate to **Discovery** --> **Models** in the left sidebar
2. Search for **gpt-4o**

### Step 2: Deploy the Model

1. Click on **gpt-4o** → **Deploy**
2. Configure deployment:

   | Field | Value |
   |-------|-------|
   | Deployment name | `gpt-4o` |
   | Model version | *Latest available* |
   | Deployment type | **Global Standard** (recommended for workshop) |
   | Tokens per minute | `50K` (sufficient for workshop) |

3. Click **Deploy**

> **Tip:** Global Standard deployments offer the best availability. For production workloads, consider **Standard** (regional) deployment for data residency requirements.

### Step 3: Verify Deployment

1. Go to **Operation**, **Assets**, **Models** 
2. Confirm `gpt-4o` shows status **Succeeded**
3. Note the **Name** — the agent will reference this

---

### 1.11 Configure Connections (Optional but Recommended)

### Application Insights (Tracing)

Foundry provides built-in tracing via Azure Monitor. To enable:

1. Navigate to **Operate** (upper-right navigation) → **Admin**
2. Under your Foundry Project resource, check connected resources
3. If Application Insights is not connected, add a connection

// TODO: ** Missing Application Insights creation steps ** -> pre-creation needed

This enables the **Tracing** tab in your project for monitoring agent conversations.

### Azure Key Vault (Secrets)

By default, Foundry stores connection secrets in a **managed Key Vault**. For enterprise deployments, you can optionally bring your own Key Vault:

1. In **Operate** → **Admin** → **Connections**
2. Configure your Key Vault connection

// TODO: add info about bring your own resources

---

### 1.12 Verify RBAC Permissions

Foundry V2 uses a simplified RBAC model. The recommended starter assignment:

| Role | Scope | Purpose |
|------|-------|---------|
| **Azure AI User** | Foundry resource | Develop and interact with agents, models, evaluations |
| **Azure AI User** | Project (managed identity) | Secure automation and service access within a project |

> **Note:** `Azure AI User` replaces the older `Azure AI Developer` + `Cognitive Services OpenAI User` combination. One role now covers both data-plane actions (building agents, running evaluations) and model access.

To check:
1. Go to **Azure Portal** → your resource group → **Access control (IAM)**
2. Click **View my access**
3. Verify `Azure AI User` is assigned at the Foundry resource scope

For admin operations (creating deployments, managing projects, configuring networking), you need **Azure AI Owner** or **Contributor** at the resource scope.

---

### 1.13 Environment Summary

At the end of this module, you should have:

| Resource | Name | Status |
|----------|------|--------|
| Resource Group | `rg-ai-workshop` | Created |
| Foundry Resource | *(auto-created with project)* | Created |
| Foundry Project | `project-intelligence` | Created |
| Model Deployment | `gpt-4o` | Deployed |
| Application Insights | *(connected)* | Optional |

Record these values — you will use them in subsequent modules.

---

## Checkpoint ✓

- [ ] Foundry resource created in Australia East (V2 — no Hub)
- [ ] Project `project-intelligence` created
- [ ] GPT-4o model deployed and status is Succeeded
- [ ] Project endpoint URL copied
- [ ] RBAC permissions verified (Azure AI User role)

---

**Next:** [Module 2: Build Your First Agent (Low-Code)](02-build-agent-low-code.md)
