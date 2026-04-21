# INTERNAL — Workshop Preparation Guide

> **Audience:** Microsoft workshop delivery team only. Do not share with CIMIC participants.

---

## Workshop Details

| Field | Value |
|-------|-------|
| **Customer** | CIMIC Group |
| **Topic** | Building Intelligent AI Agents for Infrastructure Operations |
| **Platform** | Microsoft Foundry Agent Service + Azure Databricks |
| **Modules** | 5 (Foundry Setup → Agent Build → Databricks → Toolkit → E2E Demo) |
| **Content** | [README.md](README.md) (participant-facing) |

This guide covers **two delivery options**. Choose the format that best suits the audience and available time.

---

## Option A: Hands-On Workshop (Audience Builds Along)

Participants follow each module step-by-step on their own Azure subscriptions. The workshop lead demos first, then participants replicate.

### Schedule

| Time | Duration | Activity | Module | Notes |
|------|----------|----------|--------|-------|
| 09:00 | 10 min | **Welcome & Introductions** | — | Introductions, agenda, verify prerequisites |
| 09:10 | 80 min | **Foundry Overview & Setup** | [Module 1](modules/01-foundry-setup.md) | Foundry overview (what it is, why agents for infrastructure, agent concepts, governance, workshop architecture), provision resource + project, deploy GPT-4o, verify RBAC |
| 10:30 | 15 min | ☕ **Break** | — | |
| 10:45 | 90 min | **Build Your First Agent** | [Module 2](modules/02-build-agent-low-code.md) | Create Prompt agent, system prompt, File Search (2 docs), Code Interpreter, test in playground |
| 12:15 | 45 min | 🍽️ **Lunch** | — | |
| 13:00 | 90 min | **Databricks Integration** | [Module 3](modules/03-databricks-integration.md) | Load 4 tables, create Genie Space, connect MCP to Foundry, test queries. Fabric mirroring shown as demo (not hands-on). |
| 14:30 | 15 min | ☕ **Break** | — | |
| 14:45 | 60 min | **Toolkit Deep Dive** | [Module 4](modules/04-foundry-toolkit.md) | Bing Grounding (hands-on), Azure AI Search + Custom Functions (concept walkthrough only) |
| 15:45 | 15 min | ☕ **Break** | — | |
| 16:00 | 45 min | **E2E Demo + Evaluation** | [Module 5](modules/05-e2e-demo.md) | Update system prompt, run test scenarios, run Foundry batch evaluation, review results |
| 16:45 | 15 min | **Wrap-Up & Q&A** | — | Next steps, cleanup instructions, feedback |
| **17:00** | | **End** | | |

**Total: ~8 hours** (5.75 hours content + 1.5 hours breaks + 0.5 hours intro/wrap-up)

### Pre-Workshop Checklist (Delivery Team)

- [ ] Confirm all participants have Azure subscriptions with **Azure AI Owner** or **Contributor** role
- [ ] Confirm Azure Databricks workspace is provisioned in each participant's subscription (or shared workspace with per-user access)
- [ ] Pre-create resource group `rg-cimic-ai-workshop` in **Australia East** for each participant (optional — saves 5 min in Module 1)
- [ ] Verify GPT-4o model quota is available in Australia East (or participant's chosen region)
- [ ] Verify **Managed MCP Servers** preview is enabled on the Databricks workspace
- [ ] Prepare **Grounding with Bing Search** resource (one shared resource is fine — participants connect to it)

### Facilitation Tips

| Module | Common Blockers | Mitigation |
|--------|----------------|------------|
| 1 | Insufficient permissions to create Foundry resource | Pre-assign **Azure AI Owner** at subscription or RG scope |
| 1 | GPT-4o quota unavailable in Australia East | Switch to **East US 2** or **Sweden Central** — update instructions accordingly |
| 2 | File Search upload fails (large file or wrong format) | Provide pre-formatted .md files; verify files are < 512 MB |
| 3 | Databricks SQL Warehouse takes long to start | Start warehouses 30 min before Module 3; use Serverless if available |
| 3 | MCP Servers preview not enabled | Must be enabled by workspace admin before workshop — cannot be done during |
| 3 | OAuth consent prompt doesn't appear | Ensure 3rd-party cookies are enabled in browser; try Edge InPrivate |
| 4 | Bing Grounding resource creation takes time | Pre-create the Grounding with Bing Search resource; share connection string |
| 5 | Evaluation takes too long (>10 min) | Start the eval run, explain results using the pre-built demo while it completes |

### Pacing Guide

- **Module 1** — Start with the Foundry overview (Part A) to set context — explain what Foundry is, agent concepts, and the workshop architecture before touching any portal. Then move to setup (Part B); most time spent waiting for deployments. Fill wait time with Q&A about agent use cases.
- **Module 2** — Core module. Spend extra time on system prompt crafting — this is where participants engage most.
- **Module 3** — Longest module. SQL data loading can be slow on shared clusters. Have participants start in parallel. Fabric mirroring section is **demo-only** (show, don't do) unless Fabric capacity is available.
- **Module 4** — Lighter module. Bing is quick to set up. Use the concept walkthrough sections for discussion — "Where would CIMIC use AI Search? What APIs would you connect via Custom Functions?"
- **Module 5** — The payoff. Run scenarios as a group — have participants try different prompts and compare results. Evaluation is the technical highlight — walk through the JSONL dataset together.

---

## Option B: Led Demo (Audience Watches)

The workshop lead runs through the entire build while the audience observes on a shared screen. Audience participates via discussion, Q&A, and suggesting prompts during the demo.

### Schedule

| Time | Duration | Activity | Module | Notes |
|------|----------|----------|--------|-------|
| 09:00 | 10 min | **Welcome & Introductions** | — | Introductions, agenda, CIMIC scenario context |
| 09:10 | 40 min | **Foundry Overview & Setup** | [Module 1](modules/01-foundry-setup.md) | Foundry overview (what it is, why agents for infrastructure, agent concepts, governance, workshop architecture), create project, deploy model, explain V2 hierarchy. Skip waiting — use pre-provisioned resources. |
| 09:50 | 40 min | **Build the Agent** | [Module 2](modules/02-build-agent-low-code.md) | Demo: create agent, craft system prompt (involve audience), add File Search + Code Interpreter, test in playground. Invite audience to suggest test prompts. |
| 10:30 | 15 min | ☕ **Break** | — | |
| 10:45 | 40 min | **Databricks Integration** | [Module 3](modules/03-databricks-integration.md) | Demo: show pre-loaded tables, create Genie Space, connect MCP, run queries. Explain OAuth passthrough. Show Fabric mirroring briefly (5 min). |
| 11:25 | 25 min | **Toolkit Deep Dive** | [Module 4](modules/04-foundry-toolkit.md) | Demo: connect Bing Grounding, test market price query. Walk through AI Search and Custom Functions concepts — use diagrams and discussion. |
| 11:50 | 10 min | ☕ **Break** | — | |
| 12:00 | 30 min | **E2E Demo + Evaluation** | [Module 5](modules/05-e2e-demo.md) | Demo: configure full agent, run test scenarios live, show Foundry evaluation with results. Invite audience to suggest ad-hoc prompts. |
| 12:30 | 15 min | **Discussion & Q&A** | — | Next steps for CIMIC, production considerations, what-if scenarios, feedback |
| **12:45** | | **End** | | |

**Total: ~3.75 hours** (2.75 hours content + 0.5 hours breaks + 0.5 hours intro/wrap-up)

### Pre-Workshop Checklist (Delivery Team)

Everything must be **pre-built and tested** before the session. The audience sees the finished product being assembled, not debugging.

- [ ] **Foundry resource + project** provisioned in Australia East (do not create live — show the creation flow, then switch to pre-built)
- [ ] **GPT-4o** deployed and verified
- [ ] **Agent `cimic-project-advisor`** created with full system prompt from Module 5
- [ ] **File Search** configured with both documents uploaded and indexed
- [ ] **Code Interpreter** enabled
- [ ] **Databricks workspace** with all 4 tables loaded and verified:
  - `cimic.projects.financials` (10 rows)
  - `cimic.equipment.equipment_telemetry` (10 rows)
  - `cimic.safety.incidents` (7 rows)
  - `cimic.procurement.materials` (10 rows)
- [ ] **Genie Space** `CIMIC Project Intelligence` created with all 4 tables, instructions, and example queries
- [ ] **SQL Warehouse** started and warm (start 30 min before session)
- [ ] **MCP connection** configured and OAuth authorised (consent completed)
- [ ] **Grounding with Bing Search** resource created and connected to agent
- [ ] **Evaluation dataset** `cimic-eval-dataset.jsonl` uploaded and ready
- [ ] **Pre-run one evaluation** so you can show completed results instantly if the live run is slow
- [ ] Test all 6 scenarios from Module 5 end-to-end — note any slow or inconsistent responses
- [ ] Prepare a **backup screen recording** (10 min) of the E2E demo in case of live environment issues

### Facilitation Tips

| Section | Tip |
|---------|-----|
| Module 1 | Show the portal creation flow briefly, then switch to the pre-built environment. Spend time on the **V2 resource hierarchy** diagram — this is what architects care about. |
| Module 2 | **Involve the audience** when writing the system prompt. Ask: "What instructions should we give the agent about safety?" This drives engagement. |
| Module 3 | The data setup SQL is boring to watch. Show the tables **already loaded** and focus on the Genie Space + MCP connection. Run live queries and let the audience suggest questions. |
| Module 4 | Bing Grounding demo is quick and impressive (real-time market data). Use the concept sections as **discussion prompts** — "If CIMIC has 50,000 documents in SharePoint, which tool handles that?" |
| Module 5 | This is the main event. Run scenarios **slowly** — show the tool calls in the trace panel. Let the audience see the agent deciding which tool to use. For evaluation, show the portal dashboard and walk through per-query scores. |
| Q&A | Have production readiness checklist (Section 5.6) ready to screen-share. Common questions: "How does row-level security work?", "What's the cost?", "Can it write data back?" |

### Narrative Arc

Structure the demo as a **story**, not a feature walkthrough:

1. **The problem** (intro) — "CIMIC has project data across Databricks, policies in documents, and market data on the web. A project manager needs answers that span all three."
2. **The foundation** (M1-M2) — "We set up a Foundry project and give the agent a persona — it knows CIMIC's divisions, terminology, and response guidelines."
3. **The data** (M3) — "We connect it to Databricks via Genie MCP — zero code, per-user security. The agent can now query 4 tables of live operational data."
4. **The context** (M4) — "We add Bing for real-time market data. We discuss where AI Search and Custom Functions fit for future expansion."
5. **The payoff** (M5) — "Now watch it answer a real executive question — pulling financials from Databricks, safety data from another table, weather from Bing, and generating a chart with Code Interpreter. One question, four tools, one coherent answer."
6. **The quality gate** (M5 eval) — "And here's how we ensure it stays accurate — Foundry's built-in evaluation scores every response against relevance, task adherence, and tool accuracy."

---

## Option Comparison

| Dimension | Option A (Hands-On) | Option B (Led Demo) |
|-----------|--------------------|--------------------|
| **Duration** | ~8 hours (full day) | ~3.75 hours (half day) |
| **Audience size** | 5–15 participants | Any size |
| **Azure subscriptions needed** | 1 per participant | 1 (presenter's) |
| **Databricks workspaces needed** | 1 per participant (or shared with per-user access) | 1 (presenter's) |
| **Audience engagement** | High — building it themselves | Medium — watching + discussion + suggesting prompts |
| **Risk of blockers** | Higher — permissions, quotas, network issues | Low — everything pre-built |
| **Learning depth** | Deep — participants remember what they built | Moderate — participants understand concepts and see results |
| **Prep effort** | Medium — verify participant access, test modules | High — full pre-build required, backup recording |
| **Best for** | Technical teams who will build agents themselves | Executives, architects, mixed-technical audiences |

### Hybrid Approach

If time allows (~5–6 hours), combine both:

| Time | Activity | Format |
|------|----------|--------|
| 09:00–09:15 | Welcome & Overview | Presentation |
| 09:15–10:15 | Modules 1–2: Foundry + Agent | **Hands-on** (participants build) |
| 10:15–10:30 | Break | |
| 10:30–11:30 | Module 3: Databricks Integration | **Led demo** (complex setup — presenter drives, audience follows along conceptually) |
| 11:30–12:15 | Lunch | |
| 12:15–13:00 | Module 4: Toolkit | **Hands-on** for Bing, **discussion** for concepts |
| 13:00–13:15 | Break | |
| 13:15–14:15 | Module 5: E2E Demo + Eval | **Led demo** on pre-built agent (presenter runs scenarios, audience suggests prompts) |
| 14:15–14:30 | Wrap-Up & Q&A | Discussion |

**Total: ~5.5 hours** (4 hours content + 1 hour breaks + 0.5 hours intro/wrap-up)

---

## Azure Resource Costs (Estimate)

Resources used during the workshop and approximate costs:

| Resource | SKU | Est. Cost (Workshop Day) | Notes |
|----------|-----|-------------------------|-------|
| Foundry Resource (AI Services) | Standard | ~$0 (pay-per-token) | Only charged for model inference |
| GPT-4o tokens | Global Standard | ~$5–15 per participant | Depends on prompt volume |
| Azure Databricks | Serverless SQL Warehouse | ~$10–20 per participant | Billed per DBU; Serverless auto-stops |
| Grounding with Bing Search | S1 | ~$3/1K transactions | Shared across all participants |
| Application Insights | Pay-as-you-go | < $1 | Minimal tracing data |
| **Total per participant** | | **~$20–40** | For a full-day hands-on session |

> **Cleanup reminder:** Delete `rg-cimic-ai-workshop` resource group after the workshop to stop all charges. Include this in wrap-up for hands-on participants.

---

## Contacts

| Role | Name | Responsibility |
|------|------|---------------|
| Workshop Lead | | Delivers the workshop, runs demos |
| Technical Support | | Assists participants with Azure/Databricks issues |
| CIMIC Sponsor | | Business context, CIMIC-specific Q&A |
| Microsoft Account Team | | Relationship management, follow-up |
