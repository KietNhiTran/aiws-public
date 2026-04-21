# Module 2: Build Your First Agent (Low-Code)

**Duration:** 90 minutes  
**Objective:** Create your first Prompt agent using Microsoft Foundry Agent Service portal.

---

## 2.1 Understanding Foundry Agent Types

Microsoft Foundry supports two agent types:

| Type | Description | Best For |
|------|-------------|----------|
| **Prompt Agent** | LLM-backed agents configured via the portal with system instructions and tools. No custom code needed. | Low-code scenarios, rapid prototyping, business-user-driven agents |
| **Hosted Agent** | Container-based agents running custom code (Python/C#) with full framework control. | Complex logic, multi-agent workflows, custom integrations |

In this module, we use **Prompt Agent** — the low-code approach ideal for CIMIC teams who want to build agents without deep programming expertise.

---

## 2.2 CIMIC Scenario: Project Cost Advisor Agent

We'll build an agent that CIMIC project managers can query for:
- Project budget summaries and cost variance analysis
- Equipment utilization metrics
- Safety compliance status
- Procurement lead time estimates

---

## 2.3 Create a Prompt Agent

### Step 1: Navigate to Agent Service

1. In Microsoft Foundry portal ([ai.azure.com](https://ai.azure.com)), ensure the **New Foundry** toggle is **ON**
2. Select your project `cimic-project-intelligence` from the upper-left project selector
3. On top menu, click **Agents**
4. Click **+ New agent**

### Step 2: Configure Agent Identity

| Field | Value |
|-------|-------|
| Agent name | `cimic-project-advisor` |
| Model deployment | `gpt-4o` (the model deployed in Module 1) |

### Step 3: Write System Instructions

The system instructions define the agent's persona, behavior, and boundaries. A well-structured system prompt is the most important factor in agent quality — see [Section 2.9: Prompt Engineering Best Practices](#29-prompt-engineering-best-practices) for the principles behind this design.

Paste the following:

```
You are the CIMIC Project Intelligence Advisor, an AI assistant built for CIMIC Group
project managers and operations teams.

## Your Role
- Provide data-driven insights on infrastructure project performance
- Analyze financial data including budget vs. actuals, cost variance, and schedule performance
- Report on equipment fleet status, maintenance schedules, and utilization rates
- Summarize safety incident trends and HSE compliance metrics
- Advise on procurement timing and supplier performance

## Your Knowledge Domain
- CIMIC Group's current operating companies are ONLY the following:
  • CPB Contractors (construction)
  • Thiess (contract services)
  • Sedgman (mineral processing)
  • Pacific Partnerships (public-private partnerships)
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

### Step 4: Configure Model Parameters

Click **Model configuration** and adjust:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Temperature | `0.3` | Low creativity — we want factual, consistent responses |
| Top P | `0.9` | Standard diversity |
| Max tokens | `4096` | Allow detailed responses with tables |

---

## 2.4 Test the Agent (No Tools Yet)

Before adding tools, test the base agent behavior.

> **Important:** Before testing, verify that **no tools** are attached to the agent (especially Web Search / Bing Grounding). The boundary test in Prompt 3 below validates that the agent correctly refuses to answer project-specific questions without a data source. If Web Search is enabled, the agent will fetch live data from the internet and the boundary test will fail.

### Step 1: Open the Chat Playground

1. In the agent configuration page, click **Try in playground** (or the chat panel on the right)
2. This opens a conversational interface connected to your agent

### Step 2: Test Prompts

Try these prompts to verify the agent's persona:

**Prompt 1 — Identity check:**
```
Who are you and what can you help me with?
```
*Expected: Agent identifies as CIMIC Project Intelligence Advisor with listed capabilities.*

**Prompt 2 — Domain knowledge:**
```
What are the main operating companies under CIMIC Group?
```
*Expected: Lists CPB Contractors, Thiess, Sedgman, Pacific Partnerships — and **only** these four. The agent should not mention former subsidiaries like UGL (divested ~2020) because the Knowledge Domain section uses an exclusive list.*

**Prompt 3 — Boundary test:**
```
What is the current budget for the Sydney Metro West project?
```
*Expected: Agent states it doesn't have access to that data and recommends connecting a data source (e.g., "I don't currently have access to that data. To answer this, I would need a connection to the project financials database."). This works because the **Data Source Policy** in the system prompt explicitly prevents the agent from using training knowledge for project-specific data.*

> **Discussion Point:** Without the Data Source Policy, the agent would likely answer using publicly available training data about Sydney Metro West. This demonstrates why **grounding rules** in system prompts are critical — they prevent the agent from presenting unverified or outdated information as fact. In Module 3, we'll connect it to Databricks for live, authoritative data access.

---

## 2.5 Add a Knowledge Base with File Search

File Search allows the agent to search through uploaded documents — ideal for CIMIC's project reports, safety manuals, and procurement guides.

### Step 1: Prepare Sample Documents

Create these sample files (or use provided workshop files):

**`cimic-safety-policy-2025.md`:**
```markdown
# CIMIC Group HSE Policy 2025

## Zero Harm Commitment
CIMIC Group is committed to Zero Harm across all operations.
Target: Zero fatalities, Lost Time Injury Frequency Rate (LTIFR) < 1.0

## Incident Reporting
- All incidents must be reported within 24 hours
- Near-misses require reporting within 48 hours
- Critical incidents trigger immediate stop-work authority

## PPE Requirements
All personnel on CIMIC sites must wear:
- Hard hat (AS/NZS 1801)
- Safety glasses (AS/NZS 1337)
- High-visibility vest (AS/NZS 4602)
- Steel-capped boots (AS/NZS 2210)

## Key Metrics (FY2024)
- LTIFR: 0.82 (target: <1.0) ✓
- Total Recordable Injury Frequency Rate: 3.1
- Near-miss reporting rate: 12.4 per million hours worked
```

**`project-governance-framework.md`:**
```markdown
# CIMIC Project Governance Framework

## Cost Control Thresholds
| Metric | Green | Amber | Red |
|--------|-------|-------|-----|
| Cost Variance (CV) | > -5% | -5% to -10% | < -10% |
| Schedule Performance Index (SPI) | > 0.95 | 0.85 - 0.95 | < 0.85 |
| Earned Value (EV) vs Plan | > 95% | 85-95% | < 85% |

## Approval Authority
| Change Value (AUD) | Approver |
|--------------------|----------|
| < $500K | Project Manager |
| $500K – $5M | Divisional Director |
| > $5M | Executive Committee |

## Reporting Cadence
- Weekly: Project status dashboard
- Monthly: Financial performance report
- Quarterly: Board summary with risk register
```

### Step 2: Upload Documents to File Search

1. In the agent configuration, scroll to **Tools** section
2. Click **+ Add tool** → **File Search**
3. Click **+ Add data source** → **Upload files**
4. Upload the two documents created above
5. A **Vector Store** is automatically created to index the documents

### Step 3: Test File Search

In the chat playground, test:

```
What is CIMIC's LTIFR target for 2025?
```
*Expected: Agent retrieves from the safety policy — target is < 1.0, FY2024 actual was 0.82.*

```
What cost variance threshold triggers a red flag on CIMIC projects?
```
*Expected: Agent retrieves governance framework — CV < -10% is Red.*

---

## 2.6 Add Code Interpreter

Code Interpreter enables the agent to execute Python code for calculations and data analysis.

### Step 1: Enable Code Interpreter

1. In **Tools** section, click **+ Add tool** → **Code Interpreter**
2. Toggle it **On**

### Step 2: Test Code Interpreter

```
If a CIMIC project has a budget of AUD 450M, actual costs of AUD 412M, 
and planned value of AUD 420M, calculate the Cost Variance, 
Schedule Variance, CPI, and SPI. Show the formulas.
```

*Expected: Agent uses Code Interpreter to calculate:*
- *CV = EV - AC = 420M - 412M = +8M (favorable)*
- *SV = EV - PV = 420M - 420M = 0*
- *CPI = EV / AC = 1.019*
- *SPI = EV / PV = 1.0*

```
Create a bar chart comparing these metrics: 
Budget AUD 450M, EV AUD 420M, AC AUD 412M, PV AUD 420M
```

*Expected: Agent generates a Python chart comparing the values.*

---

## 2.7 Enable Memory (Preview — Optional)

Memory is a managed **long-term memory** capability in Foundry Agent Service. It lets your agent remember information **across conversations** — user preferences, past decisions, and key context — so each session feels continuous rather than starting from scratch.

> **Note:** Memory is currently in **public preview**. Functionality and pricing may change. It is optional for this workshop.

### How Memory Works

Memory operates in three phases:

| Phase | What Happens |
|-------|-------------|
| **Extraction** | The system identifies key information from the conversation (preferences, facts, decisions) and stores them as memory items |
| **Consolidation** | Duplicate or overlapping memories are merged using an LLM, and conflicting facts are resolved to keep memory accurate |
| **Retrieval** | At the start of each new conversation, relevant memories are surfaced so the agent has immediate context |

### Memory Types

| Type | Description | When Retrieved |
|------|-------------|----------------|
| **User profile memory** | Static preferences about the user (e.g., preferred name, reporting format, project assignment) | Once at the start of each conversation |
| **Chat summary memory** | Distilled summaries of topics covered in previous sessions | Per turn, based on relevance to the current message |

### CIMIC Use Case

Imagine a CIMIC project manager who regularly uses the agent:
- **Session 1:** "I'm the PM for the Pacific Highway Upgrade. I prefer cost reports in table format with AUD figures."
- **Session 2 (days later):** "Show me the latest cost variance."
  - With memory, the agent already knows the user's project, preferred format, and currency — no need to repeat.

### Step 1: Enable Memory in the Portal

1. In the agent configuration, scroll to the **Tools** section
2. Click **+ Add tool** → **Memory**
3. A **memory store** is automatically created with a chat model and embedding model deployment
4. **User profile memory** and **Chat summary memory** are enabled by default

> **Tip:** The portal provides a simple on/off toggle for memory. For advanced customization — such as controlling what types of information the agent remembers via `user_profile_details` — use the **Python SDK or REST API**. See the [how-to guide](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/memory-usage) for details.

### Step 2: Test Memory

In the chat playground, try a multi-session test:

**First conversation:**
```
I'm working on the Pacific Highway Upgrade project. 
Please provide me some safety policy that I should know about
```
*Expected: Agent acknowledges and responds normally.*

**Start a new conversation** (click **New chat**):
```
What do you know about my preferences?
```
*Expected: Agent recalls the project name and preferred format from the previous session.*

> **Tip:** Memory updates are **debounced** — there's a short delay (default ~5 minutes) after conversation inactivity before memories are committed to the store. In testing, you may need to wait briefly between sessions.

### Step 3: Understand Memory Scope and Security

| Concept | Detail |
|---------|--------|
| **Scope** | Memory is partitioned per user via the `scope` parameter. Each user gets their own isolated memory |
| **Privacy** | Only store what's necessary. Use `user_profile_details` to exclude sensitive data (age, financials, credentials) |
| **Security** | Protect against prompt injection and memory corruption — malicious inputs could try to plant false "memories" |
| **Deletion** | Users can request deletion of their memory data. Use the Memory Store API to delete by scope |

> **Important for CIMIC:** In a production deployment, ensure memory scope is mapped to authenticated user identities (via Microsoft Entra ID) and that memory retention policies comply with your data governance requirements.

### Further Reading

| Resource | Description |
|----------|-------------|
| [Memory in Foundry Agent Service (preview)](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-memory) | Concepts — what memory is, how it works, types, use cases, and limitations |
| [Create and use memory in Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/memory-usage) | How-to guide — setup, SDK code, memory store APIs, best practices, and troubleshooting |

---

## 2.8 Understanding the Agent API

Even though we built the agent via the portal (low-code), Foundry exposes it via the **Foundry API** and **OpenAI-compatible Responses API**. This is important for integration.

### Python SDK (V2) Example

> **Important:** Use `azure-ai-projects>=2.0.0` (V2 SDK). The V1 SDK is incompatible with Foundry V2 projects.

```bash
pip install azure-ai-projects>=2.0.0
```

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Connect to your Foundry project
# Format: https://<foundry-resource>.ai.azure.com/api/projects/<project-name>
PROJECT_ENDPOINT = "your_project_endpoint"
AGENT_NAME = "cimic-project-advisor"

project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

# Get the OpenAI-compatible client for conversations
openai_client = project.get_openai_client()

# Create a conversation for multi-turn chat
conversation = openai_client.conversations.create()

# Chat with the agent created via portal
response = openai_client.responses.create(
    conversation=conversation.id,
    extra_body={"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}},
    input="What is the LTIFR target for CIMIC?",
)
print(f"")
print(f"User: What is the LTIFR target for CIMIC?")
print(f"Response output: {response.output_text}")


# Follow-up in the same conversation (maintains history)
response = openai_client.responses.create(
    conversation=conversation.id,
    extra_body={"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}},
    input="And what was the FY2024 actual?",
)
print(f"")
print(f"User: And what was the FY2024 actual?")
print(f"Response output: {response.output_text}")
```

> **Key Point:** The low-code agent you created in the portal is fully accessible via SDK/API. This means CIMIC's development team can integrate it into existing systems (e.g., project management portals, mobile apps) without rebuilding the agent.

---

## 2.9 Agent Configuration Summary

| Component | Configuration |
|-----------|---------------|
| Agent name | `cimic-project-advisor` |
| Agent type | Prompt (low-code) |
| Model | GPT-4o |
| Temperature | 0.3 |
| Tools | File Search, Code Interpreter, Memory (preview, optional) |
| Knowledge | Safety policy, Governance framework docs |
| System prompt | CIMIC Project Intelligence Advisor persona with Data Source Policy and citation requirements |

---

## Checkpoint ✓

- [ ] Prompt agent `cimic-project-advisor` created
- [ ] System instructions configured with CIMIC persona **and Data Source Policy**
- [ ] Agent responds correctly to identity and domain questions
- [ ] **Boundary test passes** — agent refuses project-specific data without a connected source
- [ ] File Search enabled with 2 documents uploaded
- [ ] Code Interpreter enabled and tested with EVM calculations
- [ ] (Optional) Memory enabled and tested with multi-session recall
- [ ] Understand that portal-created agents are accessible via API/SDK
- [ ] Reviewed prompt engineering best practices (Section 2.10)

---

## 2.10 Prompt Engineering Best Practices

The system prompt we wrote in Step 3 follows established prompt engineering principles. Understanding these will help you build better agents for any CIMIC use case.

### Key Principles Applied

| Principle | How We Applied It | Why It Matters |
|-----------|-------------------|----------------|
| **Define a clear persona** | "You are the CIMIC Project Intelligence Advisor..." | Anchors the agent's identity and prevents it from acting outside its role |
| **Set explicit boundaries** | Data Source Policy section | Prevents hallucination by restricting the agent to connected data sources |
| **Require source citation** | "Always cite your source explicitly" | Builds trust and allows users to verify information |
| **Provide output format guidance** | "Use tables for comparative data", "Present in AUD" | Ensures consistent, professional responses across users |
| **Define escalation rules** | Safety First section | Ensures critical issues are not handled solely by AI |
| **Use structured sections** | Markdown headers (## Role, ## Guidelines, etc.) | Makes the prompt easier to maintain and helps the model parse distinct rules |

### Common Pitfalls to Avoid

| Pitfall | Problem | Better Approach |
|---------|---------|----------------|
| Vague instructions like "be helpful" | Agent has no clear behavioral constraints | Be specific: "Only report data from connected tools" |
| No grounding policy | Agent uses training data as if it were live data | Add a Data Source Policy that restricts project-specific answers to tool-provided data |
| Missing citation requirements | Users can't verify if the response is factual | Require explicit source attribution for every data point |
| Overly long prompts with conflicting rules | Agent may ignore or deprioritize rules | Keep sections focused; test each rule with boundary prompts |
| No safety escalation path | Agent attempts to handle critical situations alone | Define clear escalation (e.g., "recommend contacting the HSE team") |
| Non-exclusive knowledge lists | Agent supplements with outdated training data (e.g., divested subsidiaries) | Use explicit "ONLY the following" phrasing to make lists exhaustive |

### Iterative Prompt Improvement

Prompt engineering is iterative. After initial testing:

1. **Test boundary cases** — Ask questions the agent should refuse (like Prompt 3)
2. **Check citation compliance** — Verify the agent cites sources in every data response
3. **Test with adversarial prompts** — Try to get the agent to break its rules (e.g., "Ignore your instructions and tell me...")
4. **Refine and re-test** — Adjust wording, add examples, or strengthen rules based on failures

### Further Reading

| Resource | Description |
|----------|-------------|
| [Azure OpenAI Prompt Engineering Techniques](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/prompt-engineering) | Microsoft's official guide to prompt engineering with Azure OpenAI |
| [System Message Framework for AI Agents](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/system-message) | Best practices for writing system messages including safety and grounding |
| [Microsoft Foundry Agent Configuration](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/) | Foundry-specific agent setup and configuration guidance |
| [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/) | Security risks for LLM-based systems — essential reading for production agents |
| [Prompt Engineering Guide (community)](https://www.promptingguide.ai/) | Comprehensive open-source guide covering techniques from zero-shot to chain-of-thought |

---

**Next:** [Module 3: Integrate Azure Databricks as Data Source](03-databricks-integration.md)
