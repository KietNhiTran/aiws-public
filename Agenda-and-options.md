# Foundry AI Workshop

---

## Workshop Details

| Field | Value |
|-------|-------|
| **Outcome** | Building Intelligent AI Agents for Infrastructure Operations |
| **Platform** | Microsoft Foundry Agent Service + Azure Databricks |
| **Modules** | 5 (Foundry overview and Setup → Agent Build → Databricks → Toolkit → E2E Demo final agent) |

This proposal covers **two delivery options**. Choose the format that best suits the audience and available time.

<div style="page-break-before: always;"></div>

---

## Option A: Led Demo (Audience Watches)

The workshop lead runs through the entire build while the audience observes on a shared screen. Audience participates via discussion, Q&A, and suggesting prompts during the demo.

### Schedule

| Time | Duration | Activity | Module | Notes |
|------|----------|----------|--------|-------|
| 09:00 | 10 min | **Welcome & Introductions** | — | Introductions, agenda, scenario context |
| 09:10 | 40 min | **Foundry Overview & Setup** | [Module 1](modules/01-foundry-setup.md) | Foundry overview (what it is, agent concepts, governance, workshop architecture), create project, deploy model, explain V2 hierarchy. |
| 09:50 | 40 min | **Build the Agent** | [Module 2](modules/02-build-your-first-agent.md) | Demo: create agent, craft system prompt, add File Search + Code Interpreter, test in playground. Invite audience to suggest test prompts. |
| 10:30 | 15 min | ☕ **Break** | — | |
| 10:45 | 60 min | **Databricks Integration** | [Module 3](modules/03-databricks-integration.md) | 2 Integration options. Demo with option 1: with pre-loaded simulated data tables, create Genie Space, connect MCP, Identity passthrough (RLS), test. Explain OAuth passthrough. Show Fabric mirroring briefly. |
| 11:45 | 25 min | **Toolkit Deep Dive** | [Module 4](modules/04-foundry-toolkit.md) | Demo: connect Bing Grounding, test market price query. Walk through AI Search and Custom Functions concepts — use diagrams and discussion. |
| 12:10 | 10 min | ☕ **Break** | — | |
| 12:20 | 30 min | **E2E Demo + Evaluation** | [Module 5](modules/05-e2e-demo.md) | Demo: configure full agent, run test scenarios live, show Foundry evaluation with results. Invite audience to suggest ad-hoc prompts. |
| 12:50 | 15 min | **Discussion & Q&A** | — | Next steps discussion, feedback |
| **13:05** | | **End** | | |

**Total: ~4.05 hours** (3 hours content + 0.5 hours breaks + 0.5 hours intro/wrap-up)
<div style="page-break-before: always;"></div>

---
## Option B: Hands-On Workshop (Audience Builds Along)

Participants follow each module step-by-step on their own Azure subscriptions or shared resource as a group work. The workshop lead demos first, then participants replicate.

### Schedule

| Time | Duration | Activity | Module | Notes |
|------|----------|----------|--------|-------|
| 09:00 | 10 min | **Welcome & Introductions** | — | Introductions, agenda, verify prerequisites |
| 09:10 | 80 min | **Foundry Overview & Setup** | [Module 1](modules/01-foundry-setup.md) | Foundry overview (what it is, agent concepts, governance, workshop architecture), provision resource + project, deploy GPT-4o, verify RBAC |
| 10:15 | 15 min | ☕ **Break** | — | |
| 10:30 | 90 min | **Build Your First Agent** | [Module 2](modules/02-build-your-first-agent.md) | Create agent, system prompt, File Search (2 docs), Code Interpreter, test in playground |
| 12:00 | 45 min | 🍽️ **Lunch** | — | |
| 12:45 | 90 min | **Databricks Integration** | [Module 3](modules/03-databricks-integration.md) | 2 Integration options. Handon with option 1: Load 4 tables, create Genie Space, connect MCP to Foundry, Identity passthrough (RLS), test. Fabric mirroring shown as demo (not hands-on). |
| 14:15 | 15 min | ☕ **Break** | — | |
| 14:30 | 60 min | **Toolkit Deep Dive** | [Module 4](modules/04-foundry-toolkit.md) | Bing Grounding (hands-on), Azure AI Search + Custom Functions (concept walkthrough only) |
| 15:30 | 15 min | ☕ **Break** | — | |
| 15:45 | 45 min | **E2E Demo + Evaluation** | [Module 5](modules/05-e2e-demo.md) | Update system prompt, run test scenarios, run Foundry batch evaluation, review results |
| 16:30 | 15 min | **Wrap-Up & Q&A** | — | Next steps, cleanup instructions, feedback |
| **16:45** | | **End** | | |

**Total: ~7.75 hours** (5.60 hours content + 1.5 hours breaks + 0.5 hours intro/wrap-up)
### Pre-Workshop Checklist
- [ ] Confirm all participants have Azure subscriptions with **Azure AI Owner** or **Contributor** role
- [ ] Confirm Azure Databricks workspace is provisioned in each participant's subscription (or shared workspace with per-user access)
- [ ] Pre-create resource group `rg-ai-workshop` in your preferred region for each participant (optional — saves 5 min in Module 1)
- [ ] Verify **Managed MCP Servers** preview is enabled on the Databricks workspace
- [ ] Prepare **Grounding with Bing Search** resource (one shared resource is fine — participants connect to it - optional if we don't want to follow this part)

---

## Option Comparison

| Dimension | Option B (Hands-On) |  Option A (Led Demo) |
|-----------|--------------------|--------------------|
| **Duration** | ~7.75 hours (full day) | ~4 hours (half day) |
| **Audience size** | 5–15 participants | Any size |
| **Azure subscriptions needed** | 1 per group | 2 (presenter's) |
| **Databricks workspaces needed** | 1 per participant (or shared with per-user access) | 2 (presenter's) |
| **Audience engagement** | High | Medium — watching + discussion + suggesting prompts |
| **Risk of blockers** | Higher — resource availability, permissions, quotas, network issues | Low — everything prepared on workshop lead env |
| **Best for** | Technical teams who will build agents themselves | Executives, architects, mixed-technical audiences |

---

## Workshop Leads

| Role | Name | Responsibility |
|------|------|---------------|
| Workshop Lead | _Your Name_ | Delivers the workshop, runs demos |

