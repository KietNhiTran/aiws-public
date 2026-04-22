# Module 4: Azure Foundry Toolkit Deep Dive

**Duration:** 60 minutes  
**Objective:** Explore the full range of built-in tools available in Microsoft Foundry Agent Service. Enable **Web Search** for use in the E2E demo, and walk through **Azure AI Search**, **Azure Functions**, **OpenAPI Tools**, and **Agent-to-Agent (A2A)** as concepts for future extensibility.

> **Recap:** In Module 2, you configured **File Search** (company policies & governance docs) and **Code Interpreter** (EVM calculations). In Module 3, you connected **Databricks Genie via MCP** (project financials, equipment telemetry, safety incidents, procurement). This module rounds out your understanding of the toolkit.

---

## 4.1 Foundry Agent Service Tool Ecosystem

Here's the full picture of tools available in Foundry Agent Service.

```
┌──────────────────────────────────────────────────────────────────────┐
│                   Foundry Agent Service                              │
│                                                                      │
│  Already configured (Modules 2 & 3):                                 │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐     │
│  │    Code      │ │    File      │ │   Databricks Genie       │     │
│  │  Interpreter │ │   Search     │ │   (MCP Tool)             │     │
│  │  (Module 2)  │ │  (Module 2)  │ │   (Module 3)             │     │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘     │
│                                                                      │
│  ★ Configured in this module (used in E2E demo):                     │
│  ┌──────────────────┐                                                │
│  │   Web Search     │                                                │
│  │  (Section 4.2)   │                                                │
│  └──────────────────┘                                                │
│                                                                      │
│  Concept walkthrough (not in E2E demo):                              │
│  ┌──────────────────┐ ┌───────────────────┐ ┌────────────────────┐  │
│  │   Azure AI       │ │  Azure Functions  │ │  Agent-to-Agent    │  │
│  │   Search         │ │  & OpenAPI Tools  │ │  (A2A) (Preview)   │  │
│  │  (Section 4.3)   │ │  (Section 4.4)    │ │  (Section 4.5)     │  │
│  └──────────────────┘ └───────────────────┘ └────────────────────┘  │
│                                                                      │
│  Other tools — brief overview (Section 4.6):                         │
│  ┌────────────┐ ┌────────────┐ ┌─────────────────┐ ┌────────────┐  │
│  │ SharePoint │ │   Image    │ │    Browser      │ │  Computer  │  │
│  │ (Preview)  │ │ Generation │ │   Automation    │ │    Use     │  │
│  └────────────┘ └────────────┘ └─────────────────┘ └────────────┘  │
│  ┌────────────┐ ┌─────────────────┐ ┌────────────────────────────┐  │
│  │   Deep     │ │ Custom Code     │ │   Fabric (Preview)         │  │
│  │  Research  │ │ Interpreter     │ │   (See Module 3, Option 2) │  │
│  └────────────┘ └─────────────────┘ └────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

> **Source:** [Foundry Agent Service Tool Catalog](https://learn.microsoft.com/azure/foundry/agents/concepts/tool-catalog) — the official list of all built-in and custom tools.

---

## 4.2 Web Search (Hands-On — Used in E2E Demo)

### What It Does
Gives the agent access to **real-time web search** via Bing. Useful for retrieving current information not available in your internal data sources. The Foundry Portal provides a simple **Web Search** toggle that handles everything — no additional Azure resources required.

### Use Cases

| Use Case | Example |
|----------|---------|
| Material pricing | "What is the current market price of structural steel in Australia?" |
| Regulatory changes | "Any recent changes to Australian building codes for high-rise construction?" |
| Weather impact | "Is there a severe weather warning for the Northern Basin region this week?" |
| Industry news | "Latest news about Australian infrastructure projects" |
| Competitor analysis | "What major projects has Lendlease won recently?" |

### Configuration (Portal)

#### Step 1: Enable Web Search on Your Agent

1. Open your agent `project-advisor` in the Agent Service
2. In the agent configuration panel, find the **Tools** section
3. Under **Most popular**, locate **Web search**
4. Flip the toggle to **On**

That's it — Web Search is now active on your agent. No Azure resource creation, no connection setup, no API keys.

> **💡 Tip:** Enabling the toggle makes Web Search *available*, but the agent may not always use it reliably — the system prompt from Module 2 steers it toward internal data sources first. If Web Search doesn't fire consistently during testing, see **[Appendix: Troubleshooting Web Search](#appendix-troubleshooting-web-search)** at the end of this module for an adjusted system prompt you can copy-paste.

### When to Use Web Search vs. Internal Data

| Scenario | Use Web Search? | Use File Search / Genie? |
|----------|-----------------|--------------------------|
| Current market prices | Yes | No |
| Internal project data | No | Yes (Genie MCP) |
| Regulatory updates | Yes | No (unless you index regulations) |
| Internal company policies | No | Yes (File Search) |
| General industry news | Yes | No |
| Weather conditions for site visits | Yes | No |

### Test Web Search

Try these prompts in the agent playground:

```
What is the current Australian Government infrastructure pipeline 
for 2025-2026? Cite sources.
```

```
What is the current market price of structural steel in Australia?
```

```
Are there any severe weather warnings for the Northern Basin region this week?
```

### Web Search vs. Bing Grounding — When to Upgrade

The Foundry Portal also offers a **Bing Grounding** tool that requires a dedicated **Grounding with Bing Search** Azure resource. Both tools use Bing under the hood and both send data **outside** the Azure compliance boundary. For this workshop, the simple Web Search toggle is all we need. Here's the comparison so you know when your team might upgrade:

| | Web Search (this workshop) | Bing Grounding (resource-based) |
|---|---|---|
| **Setup** | Zero — just flip the toggle on | Requires creating a Grounding with Bing Search resource in Azure and connecting it to Foundry |
| **Bing resource** | Managed by Microsoft (shared, invisible) | Managed by you — your own dedicated Azure resource with keys and endpoint |
| **Search parameters** | `user_location` (geo-relevant results), `search_context_size` (low / medium / high) | `count` (number of results), `freshness` (time window), `market` (region/language), `set_lang` — fine-grained control over search behaviour |
| **Model support** | Azure OpenAI models only | Azure OpenAI models **and** Azure direct models (non-OpenAI models deployed on Azure, e.g., Llama, Mistral) |
| **Cost visibility** | Included in usage — harder to attribute per-resource | Metered on your own Azure resource — visible in Cost Management and attributable to a specific resource/tag |
| **Access control (RBAC)** | Subscription-level on/off via `az feature register`; no per-resource RBAC | Full Azure RBAC on the Bing resource — Contributor/Owner to create/manage, Azure AI Project Manager to connect |
| **Network isolation** | ❌ Acts as a public endpoint (does not respect VPN or private endpoints) | ❌ Also acts as a public endpoint (does not respect VPN or private endpoints) |
| **Domain-restricted search** | Supported (GA) — define allowed/blocked domains via Bing Custom Search config | Supported (Preview) — via Grounding with Bing Custom Search resource |
| **Data boundary** | Data flows outside Azure compliance boundary | Data flows outside Azure compliance boundary |
| **Best for** | Workshops, prototyping, simple agents, Azure OpenAI models | Enterprise workloads needing search control, cost attribution, multi-model support, or granular search parameters |

> **⚠ Important — Neither option supports private endpoints.** Both Web Search and Bing Grounding behave as public endpoints. If your agent runs in a network-secured Foundry project with VPN or private endpoints, web grounding requests still route over the public internet. Factor this into your security review.
>
> See the official comparison: [Web grounding tools overview](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/web-overview)

**When to consider Bing Grounding for production:**

1. **Search parameter control** — You need `market=en-AU` to prioritise Australian sources, or `freshness=Week` to limit results to recent content.
2. **Cost attribution** — Finance/IT needs per-resource cost breakdown for chargebacks.
3. **Multi-model flexibility** — You're using non-OpenAI models (Llama, Mistral, etc.) deployed on Azure.
4. **RBAC governance** — Admins need to control who creates, manages, or rotates the Bing resource keys.

---

## 4.3 Azure AI Search (Concept Walkthrough)

> **Note:** This section is a conceptual walkthrough. Azure AI Search is **not** configured in the E2E demo (Module 5), but is an important tool to understand for production deployments.

### What It Does
Connects the agent to an existing **Azure AI Search index** for enterprise-grade search with semantic ranking, filtering, and faceting. Unlike File Search (which indexes uploaded files automatically), Azure AI Search connects to external indexes you manage — enabling search across millions of documents from any data source.

### When to Use Azure AI Search vs. File Search

| Feature | File Search (Module 2) | Azure AI Search |
|---------|------------------------|-----------------|
| Data source | Files uploaded to Foundry | External search index (any data source) |
| Index management | Automatic | You manage the index |
| Scalability | Good for <10K docs | Handles millions of documents |
| Advanced features | Basic vector search | Semantic ranking, filters, facets, scoring profiles |
| Real-time updates | Manual upload | Indexer-based (auto-refresh) |
| Best for | Policies, governance docs | Large document collections, structured data search |

### Use Cases

| Use Case | Index Source | Why AI Search? |
|----------|-------------|----------------|
| **Project document search** | SharePoint / Blob Storage | Thousands of project documents across all divisions — too many for File Search |
| **Safety incident root cause analysis** | HSE database | Find similar past incidents by description, enabling pattern detection |
| **Technical specs lookup** | Engineering document library | Search material standards, construction specifications |
| **Tender document search** | Document management system | Search across historical tender submissions |

### How It Works

1. **Create an Azure AI Search resource** in your subscription
2. **Define an index schema** with fields, types, and semantic configuration
3. **Populate the index** from your data source (SQL, Blob Storage, Cosmos DB, etc.)
4. **Connect to agent** via Tools → Azure AI Search → select your resource and index

### Example: Safety Incident Search Index

In a production deployment, you would create a safety incidents index with semantic search enabled. This allows queries like "find incidents similar to hydraulic failure on excavators" — something structured SQL cannot do.

```python
# Conceptual example — index schema for safety incidents
index = SearchIndex(
    name="safety-incidents",
    fields=[
        SimpleField(name="incident_id", type="Edm.String", key=True),
        SimpleField(name="incident_date", type="Edm.DateTimeOffset", filterable=True),
        SearchableField(name="site_name", type="Edm.String", filterable=True),
        SearchableField(name="description", type="Edm.String"),        # Semantic search on this
        SearchableField(name="root_cause", type="Edm.String"),         # And this
        SearchableField(name="corrective_action", type="Edm.String"),  # And this
    ],
    semantic_search=SemanticSearch(
        configurations=[SemanticConfiguration(
            name="safety-semantic",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[
                    SemanticField(field_name="description"),
                    SemanticField(field_name="root_cause"),
                ],
            ),
        )],
    ),
)
```

**Key insight:** Azure AI Search excels at **finding similar items by description** — something structured database queries (including Genie MCP) can't do. This means a project manager reporting a new safety incident can instantly find similar past incidents across all divisions and sites.

> **When to add this to the agent:** If your organization has large document collections (10K+ docs) in SharePoint, Blob Storage, or an HSE database that would benefit from semantic search, Azure AI Search is the right tool. For this workshop, File Search handles the policy docs and Genie MCP handles the structured data.

---

## 4.4 Custom Function Tools (Concept Walkthrough)

> **Note:** This section is a conceptual walkthrough. Custom Functions are **not** built or used in the E2E demo (Module 5), but are essential for connecting to enterprise systems that don't have MCP or search integrations.

### What It Does
Custom Function Tools let you define API-based tools using **OpenAPI 3.0 specifications**. The agent calls these functions when it determines they're relevant to the user's query. This is how you connect the agent to any REST API — internal or external.

### When to Use Custom Functions vs. Genie MCP

| Scenario | Genie MCP | Custom Functions |
|----------|-----------|-----------------|
| Data in Databricks/lakehouse | ✅ Best choice | Unnecessary |
| Data in external REST API (SAP, ServiceNow, etc.) | ❌ Not applicable | ✅ Best choice |
| Complex business logic (multi-step calculations) | ❌ SQL only | ✅ Can run any code |
| Write operations (create ticket, send email) | ❌ Read-only | ✅ Supports POST/PUT |
| Real-time external data (weather API, stock prices) | ❌ | ✅ Best choice |

### How the Agent Decides to Call a Function

The agent's decision is based on:
1. **Function name** — should be descriptive (e.g., `searchSafetyIncidents`, not `getData`)
2. **Function description** — detailed explanation of what the function does and when to use it
3. **Parameter descriptions** — clear documentation of each input
4. **User's query** — matched against the above

### Best Practices for Function Definitions

```
✅ GOOD function name: "searchSafetyIncidents"
✅ GOOD description: "Search HSE safety incidents from the HSE Management System. 
   Returns incident records including severity, root cause, corrective actions, 
   and investigation status. Use for safety queries, incident analysis, and compliance checks."

❌ BAD function name: "getData"
❌ BAD description: "Gets data from the database"
```

### Custom Function Ideas (Future)

| Function | Description | Backend System |
|----------|-------------|----------------|
| `searchSafetyIncidents` | Search HSE incident records by site, severity, status | HSE Management System API |
| `getProcurementData` | Query material pricing, suppliers, lead times | SAP ERP API |
| `generateProjectReport` | Create formatted project report PDF | Report Generation Service |
| `checkWeatherForSite` | Weather conditions at construction site | Bureau of Meteorology API |
| `createMaintenanceTicket` | Raise a maintenance work order | ServiceNow / Maximo API |

### How It Works (OpenAPI Tool)

1. **Build an API** (e.g., Azure Functions, App Service, or any REST endpoint)
2. **Write an OpenAPI 3.0 spec** describing the endpoints, parameters, and responses
3. **Add to agent** via Tools → OpenAPI Tool → provide the OpenAPI spec
4. The agent reads the spec and knows when and how to call each function
5. Authentication options: anonymous, API key (stored in project connection), or managed identity

### How It Works (Azure Functions Tool)

1. **Create an Azure Function** (any supported language: Python, C#, Java, TypeScript)
2. **Choose integration pattern**: MCP server (real-time) or Queue-based (async)
3. **Add to agent** via Tools → Azure Functions → select your function app and functions
4. The agent calls the function server-side — your client app doesn't need to handle execution

### Example: OpenAPI Spec Structure

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Operations API",
    "version": "1.0.0"
  },
  "servers": [{ "url": "https://<your-api>.azurewebsites.net/api" }],
  "paths": {
    "/safety/incidents": {
      "post": {
        "operationId": "searchSafetyIncidents",
        "summary": "Search HSE safety incidents. Use for structured safety queries.",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "site": { "type": "string", "description": "Site name (e.g., Northern Basin)" },
                  "severity": { "type": "string", "enum": ["Minor", "Moderate", "Serious"] },
                  "status": { "type": "string", "enum": ["open", "closed"] }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

> **When to add this to the agent:** When you need to connect to systems that don't have Databricks/MCP integration — SAP ERP, ServiceNow, custom HSE platforms, or any internal REST API. Use **Azure Functions** when you need server-side isolation, async processing, or reusable tools across agents. Use **OpenAPI Tools** when you have an existing REST API with a spec and want the simplest integration path.

---

## 4.5 Agent-to-Agent (A2A) (Concept Walkthrough)

> **Note:** This section is a conceptual walkthrough. A2A is **not** configured in the E2E demo (Module 5), but is an important pattern for production multi-agent architectures.

### What It Does
**Agent-to-Agent (A2A)** is a custom tool (preview) that lets your agent communicate with other agents through A2A-compatible endpoints. Instead of one agent doing everything, you build specialist agents and have a coordinator route to them.

> See: [Connect to an A2A agent endpoint from Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/agent-to-agent)

### Use Case: Multi-Agent Architecture

In a production deployment, rather than a single agent with many tools, you could build specialist agents:

```
┌─────────────────────────────────────┐
│  Project Intelligence Hub            │
│  (Coordinator Agent)                │
│                                     │
│  Routes queries via A2A to:         │
│  ┌─────────────┐ ┌─────────────┐   │
│  │   Safety    │ │  Finance    │   │
│  │   Agent     │ │  Agent      │   │
│  │ (HSE data,  │ │ (EVM, cost  │   │
│  │  incidents) │ │  variance)  │   │
│  └─────────────┘ └─────────────┘   │
│  ┌─────────────┐ ┌─────────────┐   │
│  │ Procurement │ │  Equipment  │   │
│  │   Agent     │ │   Agent     │   │
│  │ (suppliers, │ │ (fleet,     │   │
│  │  materials) │ │  maintenance│   │
│  └─────────────┘ └─────────────┘   │
└─────────────────────────────────────┘
```

### How It Works

1. **Build specialist agents** — each with their own tools and system prompts tuned to a domain
2. **Create an A2A connection** in the Foundry portal: Tools → Connect tool → Catalog → Custom → Agent2Agent (A2A)
3. **Configure authentication** — key-based, Microsoft Entra, or OAuth identity passthrough
4. **Add to coordinator agent** — the coordinator decides which specialist to call based on the user's query

### When to Use A2A vs. Single Agent with Many Tools

| Scenario | Single Agent | Multi-Agent (A2A) |
|----------|-------------|-------------------|
| Workshop / prototype | ✅ Simpler to build | Overkill |
| < 5 tools | ✅ Works well | Unnecessary |
| 10+ tools, multiple domains | Tool confusion risk | ✅ Better routing |
| Different teams own different data | Shared prompt complexity | ✅ Separation of concerns |
| Different security boundaries per domain | Hard to manage | ✅ Each agent has own RBAC |
| Need to update one domain without affecting others | Risky | ✅ Independent deployment |

> **When to consider A2A:** When the single-agent approach starts hitting prompt complexity limits (too many tools, conflicting instructions), or when different teams (HSE, Finance, Procurement) want to own and evolve their agents independently.

---

## 4.6 Other Foundry Tools at a Glance

The following tools are available in Foundry Agent Service but not covered in detail in this workshop. They're listed here so you know what's available for future use.

| Tool | Status | What It Does | Relevance |
|------|--------|-------------|------------------|
| **SharePoint** | Preview | Chat with private documents stored in SharePoint using OBO (On-Behalf-Of) authentication — the agent only sees files the user has permission to access. | High — project docs, HSE records, tender archives likely live in SharePoint. Natural complement to File Search for M365-integrated document access. |
| **Image Generation** | Preview | Generate images as part of conversations using `gpt-image-1`. Requires both the image model and an LLM orchestrator in the same project. | Medium — site layout diagrams, progress visualization mockups, report illustrations. |
| **Browser Automation** | Preview | Perform real-world browser tasks through natural language prompts — automated browsing without human intervention. | Medium — extract data from government compliance portals, project management web apps, or regulatory databases. |
| **Computer Use** | Preview | Interact with computer systems through their user interfaces (requires `computer-use-preview` model). | Low — interacting with legacy desktop ERP applications that lack APIs. |
| **Deep Research** | Preview | Multi-step web-based research pipeline using `o3-deep-research` model with Bing Search. Performs extended analysis and reasoning across multiple sources. | Medium — deep-dive research on regulations, tender background, market analysis, competitor intelligence. |
| **Custom Code Interpreter** | Preview | Customize the Code Interpreter's resources, Python packages, and Container Apps environment. | Medium — pre-install engineering Python libraries (geotechnical, structural calcs) not available in the default sandbox. |
| **Fabric Data Agent** | Preview | Connect to a Microsoft Fabric data agent for data analysis. | Medium — alternative to Databricks Genie if your organization adopts Microsoft Fabric. See Module 3, Option 2. |

> **Source:** [Foundry Agent Service Tool Catalog](https://learn.microsoft.com/azure/foundry/agents/concepts/tool-catalog) and [Tool best practices (region & model support)](https://learn.microsoft.com/azure/foundry/agents/concepts/tool-best-practice)

---

## 4.7 Tool Comparison Summary

| Tool | Data Source | Setup Module | Used in E2E? | Use Case |
|------|-----------|-------------|-------------|-----------|
| Code Interpreter | Agent-generated Python | Module 2 | ✅ Yes | EVM calcs, charts |
| File Search | Uploaded documents | Module 2 | ✅ Yes | Policies, governance |
| Databricks Genie (MCP) | Databricks lakehouse | Module 3 | ✅ Yes | Financials, equipment, safety, procurement |
| **Web Search** | Public web (via Bing) | **Module 4** | ✅ Yes | Market prices, news, weather |
| Azure AI Search | External search index | Module 4 (concept) | ❌ No | Large doc collections, semantic search |
| Azure Functions | Serverless functions in Azure | Module 4 (concept) | ❌ No | Isolated business logic, async ops, reusable tools |
| OpenAPI Tool | Any REST API (via OpenAPI spec) | Module 4 (concept) | ❌ No | External systems (SAP, ServiceNow, etc.) |
| Agent-to-Agent (A2A) | Other Foundry agents | Module 4 (concept) | ❌ No | Multi-agent routing, specialist agents |
| SharePoint | M365 SharePoint sites | Module 4 (brief) | ❌ No | Project docs, HSE records (OBO auth) |
| Image Generation | gpt-image-1 model | Module 4 (brief) | ❌ No | Site diagrams, progress visualizations |
| Browser Automation | Web pages via browser | Module 4 (brief) | ❌ No | Government portals, compliance data |
| Deep Research | Web (o3-deep-research) | Module 4 (brief) | ❌ No | Regulation research, market analysis |

---

## Checkpoint ✓

- [ ] Web Search enabled and tested with market pricing query
- [ ] Understand when to use Azure AI Search vs. File Search (scale, semantic ranking)
- [ ] Understand Azure Functions (MCP / Queue patterns) vs. OpenAPI Tools for custom integrations
- [ ] Understand when Agent-to-Agent (A2A) multi-agent patterns are appropriate
- [ ] Aware of additional Foundry tools: SharePoint, Image Generation, Browser Automation, Deep Research
- [ ] Understand the full Foundry toolkit ecosystem and when each tool is appropriate

---

**Next:** [Module 5: End-to-End Demo — Project Intelligence Agent](05-e2e-demo.md)

---

## Appendix: Troubleshooting Web Search

### Problem

After enabling Web Search in Section 4.2, the agent sometimes ignores the web tool and responds with:

> *"I couldn't find specific information about [topic] in the uploaded files. I recommend consulting [external source]."*

This happens because the **Data Source Policy** in the Module 2 system prompt tells the agent to only use connected tools and documents. When the agent interprets "connected tools" narrowly (File Search, Code Interpreter, Genie MCP), it skips Web Search entirely and falls back to the refusal message.

### Root Cause

Enabling a tool toggle makes the capability *available*, but the LLM relies on the system prompt to decide *when* to invoke it. The existing Data Source Policy doesn't mention web search, so the agent underutilises it — especially when File Search returns no results first.

> **💡 Teaching Point:** This is a pattern you'll encounter repeatedly — **adding a tool without updating the system prompt leads to underutilisation**. Think of tools as capabilities and the system prompt as the routing logic.

### Fix: Updated System Prompt

Replace the **entire system instructions** on your `project-advisor` agent with the version below. The changes are in the **Data Source Policy** section (three new bullet points marked with `← NEW`):

```
You are the Project Intelligence Advisor, an AI assistant built for Contoso Construction
project managers and operations teams.

## Your Role
- Provide data-driven insights on infrastructure project performance
- Analyze financial data including budget vs. actuals, cost variance, and schedule performance
- Report on equipment fleet status, maintenance schedules, and utilization rates
- Summarize safety incident trends and HSE compliance metrics
- Advise on procurement timing and supplier performance

## Your Knowledge Domain
- Contoso Construction's operating companies are ONLY the following:
  • Contoso Build (construction)
  • Contoso Mining (contract services)
  • Contoso Engineering (mineral processing)
  • Contoso Partnerships (public-private partnerships)
- Do NOT mention former subsidiaries (e.g., UGL) unless the user specifically asks
  about historical company structure
- Projects span road/rail infrastructure, tunnelling, building construction, and resource operations
- Financial metrics follow Australian construction industry standards (AS/NZS)

## Data Source Policy
- For specific project data (budgets, costs, schedules, KPIs, incident counts, equipment
  status), ONLY use information provided by your connected tools (File Search, Code
  Interpreter, or API integrations)
- Always cite your source explicitly, for example:
  "According to [document name]..." or "Source: [file name], [section]"
- If you use general knowledge (e.g., industry standards, company structure), clearly
  label it: "Based on general domain knowledge: ..."
- Do NOT use your training knowledge to answer questions about specific project financials,
  timelines, or operational metrics — even if you believe you know the answer
- For questions about public, real-time, or current-affairs information (market prices,    ← NEW
  government announcements, weather, regulatory changes, industry news), USE the Web
  Search tool to retrieve up-to-date information from the internet
- Always cite the web source URL when presenting information from Web Search              ← NEW
- When the user's question could be answered by both internal documents AND web search,   ← NEW
  prefer internal documents for company-specific data and web search for external/public data
- If no connected tool or document provides the requested data, respond:
  "I don't currently have access to that data. To answer this, I would need
  [specific data source, e.g., a connection to the project financials database]."

## Response Guidelines
- Always cite the data source and time period when presenting numbers
- Present financial figures in AUD unless otherwise specified
- Use tables for comparative data
- Flag any metrics outside normal thresholds (e.g., cost variance > 10%, SPI < 0.9)
- When uncertain, state assumptions clearly and recommend verification
- Never fabricate or infer project-specific data from training knowledge — only report
  what your connected tools and documents provide

## Safety First
- Always prioritize safety-related queries
- Escalate any critical safety concerns with a clear recommendation to contact the HSE team
```

After pasting, re-test the prompts from Section 4.2. The agent should now invoke Web Search for public/current-affairs questions.
